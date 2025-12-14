from __future__ import annotations

import re
import logging
from dataclasses import dataclass

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.crud.scripted_response import list_active_scripted_responses
from app.crud.tenant import get_tenant_by_id
from app.crud.knowledge_base import search_kb_context
from app.crud.flow import get_flow_by_trigger
from app.services.flow_engine import process_flow, start_flow
from app.models.lead import Lead

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ChatResult:
    response: str
    source: str  # "bot" | "ai" | "flow"


class ChatManager:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def process_message(
        self, tenant_id: int, user_message: str, lead: Lead | None = None
    ) -> ChatResult:
        # 1. Check Active Flow
        if lead and lead.current_flow_id:
            flow_response = await process_flow(self._session, lead, user_message)
            if flow_response:
                return ChatResult(response=flow_response, source="flow")

        # 2. Check Flow Triggers
        flow_trigger = await get_flow_by_trigger(self._session, tenant_id, user_message)
        if flow_trigger and lead:
            flow_response = await start_flow(self._session, lead, flow_trigger)
            if flow_response:
                return ChatResult(response=flow_response, source="flow")

        scripted = await list_active_scripted_responses(
            session=self._session, tenant_id=tenant_id
        )

        normalized = user_message.lower()
        for rule in scripted:
            trigger = (rule.trigger_keyword or "").strip()
            if not trigger:
                continue

            # Minimal support for regex triggers: prefix with "re:".
            if trigger.lower().startswith("re:"):
                pattern = trigger[3:].strip()
                if pattern and re.search(pattern, user_message, flags=re.IGNORECASE):
                    return ChatResult(response=rule.response_text, source="bot")
            else:
                if trigger.lower() in normalized:
                    return ChatResult(response=rule.response_text, source="bot")

        tenant = await get_tenant_by_id(session=self._session, tenant_id=tenant_id)
        base_prompt = (
            tenant.system_prompt if tenant else None
        ) or "You are a helpful assistant."
        
        # Inject Knowledge Base Context
        kb_context = await search_kb_context(self._session, tenant_id, user_message)
        if kb_context:
            system_prompt = f"{base_prompt}\n\n{kb_context}\n\nاستخدم المعلومات أعلاه للإجابة على سؤال المستخدم."
        else:
            system_prompt = base_prompt

        ai_text = await self._call_openai_compatible_chat(
            system_prompt=system_prompt, user_message=user_message
        )
        return ChatResult(response=ai_text, source="ai")

    async def _call_openai_compatible_chat(
        self, *, system_prompt: str, user_message: str
    ) -> str:
        llm_key = settings.effective_llm_api_key()
        if not llm_key:
            logger.warning("No LLM API key configured")
            return "⚠️ الذكاء الاصطناعي غير مُعد. يرجى إضافة GROQ_API_KEY أو LLM_API_KEY في إعدادات البيئة."

        async def _list_models() -> list[str]:
            try:
                async with httpx.AsyncClient(
                    base_url=settings.llm_base_url, timeout=10.0
                ) as client:
                    resp = await client.get(
                        "/models",
                        headers={"Authorization": f"Bearer {llm_key}"},
                    )
                    resp.raise_for_status()
                    data = resp.json() or {}
                models = [
                    str(m.get("id"))
                    for m in (data.get("data") or [])
                    if m and m.get("id")
                ]
                # Keep stable ordering for fallback selection.
                return sorted(set(models))
            except Exception:
                return []

        def _pick_fallback_model(available: list[str]) -> str | None:
            if not available:
                return None
            preferred = [
                # Common Groq models (order matters)
                "meta-llama/llama-4-scout-17b-16e-instruct",
                "llama-4-scout-17b-16e-instruct",
                "llama-3.3-70b-versatile",
                "llama-3.1-70b-versatile",
            ]
            available_set = set(available)
            for name in preferred:
                if name in available_set:
                    return name
            return available[0]

        model = settings.effective_llm_model()
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "temperature": 0.3,
            "max_tokens": 1024,
        }

        headers = {
            "Authorization": f"Bearer {llm_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(
                base_url=settings.llm_base_url, timeout=30.0
            ) as client:
                logger.info(
                    f"Calling LLM at {settings.llm_base_url} with model {payload['model']}"
                )
                resp = await client.post(
                    "/chat/completions", json=payload, headers=headers
                )

                # If the configured model is invalid, try a one-time fallback from /models.
                if resp.status_code == 400:
                    body = (resp.text or "").lower()
                    if "model" in body or "not found" in body:
                        available = await _list_models()
                        fallback = _pick_fallback_model(available)
                        if fallback and fallback != payload["model"]:
                            logger.warning(
                                "Model '%s' rejected; retrying with fallback '%s'",
                                payload["model"],
                                fallback,
                            )
                            payload2 = dict(payload)
                            payload2["model"] = fallback
                            resp = await client.post(
                                "/chat/completions", json=payload2, headers=headers
                            )

                resp.raise_for_status()
                data = resp.json()

            return data["choices"][0]["message"]["content"]
        
        except httpx.HTTPStatusError as e:
            logger.error(f"LLM API error: {e.response.status_code} - {e.response.text}")
            if e.response.status_code == 401:
                return "⚠️ مفتاح API غير صالح. يرجى التحقق من إعدادات الذكاء الاصطناعي."
            elif e.response.status_code == 429:
                return "⚠️ تم تجاوز حد الطلبات. يرجى المحاولة لاحقاً."
            elif e.response.status_code == 503:
                return "⚠️ خدمة الذكاء الاصطناعي غير متاحة حالياً."
            if e.response.status_code == 400:
                return "⚠️ فشل طلب الذكاء الاصطناعي (قد يكون اسم النموذج غير صحيح). جرّب تغيير LLM_MODEL في Render."
            return f"⚠️ خطأ من خدمة AI: {e.response.status_code}"
        
        except httpx.TimeoutException:
            logger.error("LLM API timeout")
            return "⚠️ انتهت مهلة الاتصال بالذكاء الاصطناعي. يرجى المحاولة مرة أخرى."
        
        except Exception as e:
            logger.exception(f"Unexpected LLM error: {e}")
            return "⚠️ حدث خطأ غير متوقع. يرجى المحاولة لاحقاً."
