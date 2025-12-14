from __future__ import annotations

import json
import re

import httpx

from app.crud.lead import create_lead, get_lead_by_phone
from app.crud.tenant import get_tenant_by_id
from app.core.config import settings
from app.db.session import async_session_maker

_EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_PHONE_RE = re.compile(
    r"\b(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{2,4}\)?[\s.-]?)?\d{3,4}[\s.-]?\d{4}\b"
)

_NAME_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bmy\s+name\s+is\s+([a-z][a-z\s\-']{1,60})\b", re.IGNORECASE),
    re.compile(r"\bi\s+am\s+([a-z][a-z\s\-']{1,60})\b", re.IGNORECASE),
    re.compile(r"\bi'm\s+([a-z][a-z\s\-']{1,60})\b", re.IGNORECASE),
    re.compile(r"\bthis\s+is\s+([a-z][a-z\s\-']{1,60})\b", re.IGNORECASE),
]


def extract_lead_info(message: str) -> dict[str, str] | None:
    """Fast lead extraction.

    Returns a dict like {"customer_name": "...", "phone_number": "..."}.
    Regex-first for speed; can be augmented with LLM via `extract_lead_info_llm`.
    """

    phone_match = _PHONE_RE.search(message)
    if not phone_match:
        return None

    phone_number = phone_match.group(0).strip()

    customer_name: str | None = None
    for pattern in _NAME_PATTERNS:
        m = pattern.search(message)
        if not m:
            continue
        candidate = " ".join(m.group(1).strip().split())
        if candidate:
            customer_name = candidate.title()
            break

    return {"phone_number": phone_number, "customer_name": customer_name or ""}


async def extract_lead_info_llm(message: str) -> dict[str, str] | None:
    """Optional LLM-based extraction (small prompt).

    Only used if `settings.llm_api_key` is configured.
    """

    llm_key = settings.effective_llm_api_key()
    if not llm_key:
        return None

    system = (
        "You are an information extractor. "
        "Extract contact details from a chat message. "
        "Return ONLY valid JSON with keys: customer_name, phone_number. "
        "If unknown, use empty string."
    )
    user = f"Message: {message}"

    payload = {
        "model": settings.effective_llm_model(),
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.0,
    }
    headers = {"Authorization": f"Bearer {llm_key}"}

    try:
        async with httpx.AsyncClient(
            base_url=settings.llm_base_url, timeout=10.0
        ) as client:
            resp = await client.post("/chat/completions", json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        content = data["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        phone = str(parsed.get("phone_number", "") or "").strip()
        name = str(parsed.get("customer_name", "") or "").strip()
        if not phone:
            return None
        return {"phone_number": phone, "customer_name": name}
    except Exception:
        return None


async def save_lead(
    *, tenant_id: int, customer_name: str | None, phone_number: str, summary: str | None
) -> int:
    """Persists a lead and returns its database id. Updates existing if found."""

    async with async_session_maker() as session:
        # Check if exists
        existing = await get_lead_by_phone(session, tenant_id, phone_number)
        if existing:
            # Update if we have new info (e.g. name)
            if customer_name and not existing.customer_name:
                existing.customer_name = customer_name
                session.add(existing)
                await session.commit()
            return existing.id

        lead = await create_lead(
            session=session,
            tenant_id=tenant_id,
            customer_name=customer_name,
            phone_number=phone_number,
            summary=summary,
        )
        return lead.id


async def trigger_external_webhook(
    *, lead_data: dict, tenant_webhook_url: str | None
) -> None:
    """POST lead data to the tenant webhook if configured.

    Must be resilient: never raise.
    """

    if not tenant_webhook_url:
        return

    try:
        async with httpx.AsyncClient(
            timeout=settings.webhook_timeout_seconds
        ) as client:
            await client.post(tenant_webhook_url, json=lead_data)
    except Exception:
        # Swallow errors to keep background task from crashing app.
        return


async def detect_and_save_lead(*, tenant_id: int, user_message: str, sender_id: str | None = None) -> None:
    # Regex-first extraction for speed.
    info = extract_lead_info(user_message)

    # Optional LLM fallback if regex didn’t find anything.
    if info is None:
        info = await extract_lead_info_llm(user_message)

    phone_number = None
    customer_name = None

    if info:
        phone_number = (info.get("phone_number") or "").strip()
        customer_name = (info.get("customer_name") or "").strip() or None

    # Fallback to sender_id if no phone found in text
    if not phone_number and sender_id:
        phone_number = sender_id

    if not phone_number:
        return

    email = _EMAIL_RE.search(user_message)
    summary_parts: list[str] = [f"phone={phone_number}"]
    if customer_name:
        summary_parts.insert(0, f"name={customer_name}")
    if email:
        summary_parts.append(f"email={email.group(0)}")
    summary = "Captured lead: " + ", ".join(summary_parts)

    # Save lead.
    lead_id = await save_lead(
        tenant_id=tenant_id,
        customer_name=customer_name,
        phone_number=phone_number,
        summary=summary,
    )

    # Fire webhook if configured.
    async with async_session_maker() as session:
        tenant = await get_tenant_by_id(session=session, tenant_id=tenant_id)
        webhook_url = tenant.webhook_url if tenant else None

    await trigger_external_webhook(
        lead_data={
            "lead_id": lead_id,
            "tenant_id": tenant_id,
            "customer_name": customer_name,
            "phone_number": phone_number,
            "summary": summary,
            "source_message": user_message,
        },
        tenant_webhook_url=webhook_url,
    )
