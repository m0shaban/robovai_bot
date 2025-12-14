from __future__ import annotations

from typing import Any

import httpx


async def send_whatsapp_text(
    *, access_token: str, phone_number_id: str, to: str, text: str
) -> None:
    if not access_token or not phone_number_id or not to:
        return

    url = f"https://graph.facebook.com/v21.0/{phone_number_id}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text},
    }

    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.post(
            url, params={"access_token": access_token}, json=payload
        )
        resp.raise_for_status()


async def send_whatsapp_interactive(
    *,
    access_token: str,
    phone_number_id: str,
    to: str,
    body_text: str,
    quick_replies: list[dict[str, str]],
) -> None:
    """Send WhatsApp interactive buttons/list.

    quick_replies items: {"id": "...", "title": "..."}
    """
    if not access_token or not phone_number_id or not to:
        return

    items = [q for q in quick_replies if q.get("id") and q.get("title")]
    if not items:
        await send_whatsapp_text(
            access_token=access_token,
            phone_number_id=phone_number_id,
            to=to,
            text=body_text,
        )
        return

    url = f"https://graph.facebook.com/v21.0/{phone_number_id}/messages"

    # Buttons support up to 3. Lists support more.
    if len(items) <= 3:
        payload: dict[str, Any] = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": body_text},
                "action": {
                    "buttons": [
                        {
                            "type": "reply",
                            "reply": {
                                "id": str(it["id"])[:200],
                                "title": str(it["title"])[:20],
                            },
                        }
                        for it in items[:3]
                    ]
                },
            },
        }
    else:
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "interactive",
            "interactive": {
                "type": "list",
                "body": {"text": body_text},
                "action": {
                    "button": "اختيار",
                    "sections": [
                        {
                            "title": "قائمة سريعة",
                            "rows": [
                                {
                                    "id": str(it["id"])[:200],
                                    "title": str(it["title"])[:24],
                                }
                                for it in items[:10]
                            ],
                        }
                    ],
                },
            },
        }

    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.post(
            url, params={"access_token": access_token}, json=payload
        )
        resp.raise_for_status()


async def send_whatsapp_reply(
    *,
    access_token: str,
    phone_number_id: str,
    to: str,
    text: str,
    quick_replies: list[dict[str, str]] | None = None,
) -> None:
    """Try interactive first; fall back to text menu."""
    try:
        if quick_replies:
            await send_whatsapp_interactive(
                access_token=access_token,
                phone_number_id=phone_number_id,
                to=to,
                body_text=text,
                quick_replies=quick_replies,
            )
            return
    except Exception:
        # Fall back to normal text below.
        pass

    menu_text = format_quick_reply_menu_text(
        text,
        [q.get("title", "") for q in (quick_replies or [])],
    )
    await send_whatsapp_text(
        access_token=access_token,
        phone_number_id=phone_number_id,
        to=to,
        text=menu_text,
    )


def format_quick_reply_menu_text(
    text: str, quick_reply_titles: list[str] | None
) -> str:
    titles = [t.strip() for t in (quick_reply_titles or []) if t and t.strip()]
    if not titles:
        return text

    # Simple cross-channel fallback (works everywhere): append a numbered menu.
    lines = [text, "", "اختر سريعاً:"]
    for i, t in enumerate(titles[:8], start=1):
        lines.append(f"{i}) {t}")
    return "\n".join(lines)


async def send_page_message_text(
    *,
    page_access_token: str,
    recipient_id: str,
    text: str,
    quick_replies: list[dict[str, str]] | None = None,
) -> None:
    if not page_access_token or not recipient_id:
        return

    url = "https://graph.facebook.com/v21.0/me/messages"
    payload: dict[str, Any] = {
        "messaging_type": "RESPONSE",
        "recipient": {"id": recipient_id},
        "message": {"text": text},
    }

    items = [q for q in (quick_replies or []) if q.get("id") and q.get("title")]
    if items:
        # Messenger supports quick_replies as buttons that send payload.
        payload["message"]["quick_replies"] = [
            {
                "content_type": "text",
                "title": str(q["title"])[:20],
                "payload": str(q["id"])[:512],
            }
            for q in items[:10]
        ]

    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.post(
            url, params={"access_token": page_access_token}, json=payload
        )
        resp.raise_for_status()
