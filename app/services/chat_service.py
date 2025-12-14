from __future__ import annotations

import re
import logging
from dataclasses import dataclass

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.crud.scripted_response import list_active_scripted_responses
from app.crud.tenant import get_tenant_by_id

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ChatResult:
    response: str
    source: str  # "bot" | "ai"


class ChatManager:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def process_message(self, tenant_id: int, user_message: str) -> ChatResult:
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
        system_prompt = (
            tenant.system_prompt if tenant else None
        ) or "You are a helpful assistant."

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

        payload = {
            "model": settings.llm_model,
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
                logger.info(f"Calling LLM at {settings.llm_base_url} with model {settings.llm_model}")
                resp = await client.post("/chat/completions", json=payload, headers=headers)
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
            return f"⚠️ خطأ من خدمة AI: {e.response.status_code}"
        
        except httpx.TimeoutException:
            logger.error("LLM API timeout")
            return "⚠️ انتهت مهلة الاتصال بالذكاء الاصطناعي. يرجى المحاولة مرة أخرى."
        
        except Exception as e:
            logger.exception(f"Unexpected LLM error: {e}")
            return "⚠️ حدث خطأ غير متوقع. يرجى المحاولة لاحقاً."
