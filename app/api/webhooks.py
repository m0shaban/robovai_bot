from __future__ import annotations

from typing import Any

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Request,
    Response,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.crud.channel_integration import (
    get_integration_by_type_and_external_id,
    get_integration_by_verify_token,
)
from app.crud.quick_reply import list_quick_replies_for_tenant
from app.crud.quick_reply import get_quick_reply_by_id
from app.services.channel_dispatcher import generate_chat_response
from app.services.meta_service import (
    format_quick_reply_menu_text,
    send_page_message_text,
    send_whatsapp_reply,
)
from app.services.telegram_service import send_telegram_message

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/telegram/{verify_token}")
async def telegram_webhook(
    verify_token: str,
    request: Request,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    integ = await get_integration_by_verify_token(
        session=session,
        verify_token=verify_token,
        channel_types=["telegram"],
    )
    if integ is None or not integ.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Integration not found"
        )

    payload: dict[str, Any] = await request.json()

    message = payload.get("message") or {}
    text = message.get("text")
    chat = message.get("chat") or {}
    chat_id = chat.get("id")

    if not text or not chat_id:
        return {"status": "ignored"}

    reply_text, _source = await generate_chat_response(
        session=session,
        tenant_id=integ.tenant_id,
        message=str(text),
        background_tasks=background_tasks,
    )

    quick_items = await list_quick_replies_for_tenant(
        session=session, tenant_id=integ.tenant_id, active_only=True
    )
    quick_buttons = [q.title for q in quick_items][:8]

    bot_token = (integ.access_token or "").strip()
    background_tasks.add_task(
        send_telegram_message,
        bot_token=bot_token,
        chat_id=int(chat_id),
        text=reply_text,
        reply_keyboard_buttons=quick_buttons,
    )
    return {"status": "ok"}


@router.get("/meta")
async def meta_verify(
    request: Request, session: AsyncSession = Depends(get_db_session)
) -> Response:
    qp = request.query_params
    mode = qp.get("hub.mode")
    token = qp.get("hub.verify_token")
    challenge = qp.get("hub.challenge")

    if mode != "subscribe" or not token or not challenge:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification request",
        )

    integ = await get_integration_by_verify_token(
        session=session,
        verify_token=token,
        channel_types=["whatsapp", "messenger", "instagram"],
    )

    if integ is None or not integ.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid verify_token"
        )

    return Response(content=str(challenge), media_type="text/plain")


@router.post("/meta")
async def meta_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    payload: dict[str, Any] = await request.json()

    obj = payload.get("object")
    entries = payload.get("entry") or []

    # WhatsApp Cloud API
    if obj == "whatsapp_business_account":
        for entry in entries:
            changes = entry.get("changes") or []
            for ch in changes:
                value = ch.get("value") or {}
                metadata = value.get("metadata") or {}
                phone_number_id = metadata.get("phone_number_id")

                messages = value.get("messages") or []
                for msg in messages:
                    msg_type = (msg.get("type") or "").strip().lower()
                    body: str | None = None

                    if msg_type == "text":
                        text_obj = msg.get("text") or {}
                        body = text_obj.get("body")
                    elif msg_type == "button":
                        # Older style
                        btn = msg.get("button") or {}
                        body = btn.get("text")
                    elif msg_type == "interactive":
                        interactive = msg.get("interactive") or {}
                        i_type = (interactive.get("type") or "").strip().lower()
                        if i_type == "button_reply":
                            rep = interactive.get("button_reply") or {}
                            body = rep.get("id") or rep.get("title")
                        elif i_type == "list_reply":
                            rep = interactive.get("list_reply") or {}
                            body = rep.get("id") or rep.get("title")

                    from_number = msg.get("from")
                    if not phone_number_id or not body or not from_number:
                        continue

                    integ = await get_integration_by_type_and_external_id(
                        session=session,
                        channel_type="whatsapp",
                        external_id=str(phone_number_id),
                    )
                    if integ is None or not integ.is_active:
                        continue

                    # If body is a quick reply id, map it to payload_text.
                    mapped_body = str(body)
                    try:
                        qr_id = int(str(body))
                        qr = await get_quick_reply_by_id(
                            session=session, quick_reply_id=qr_id
                        )
                        if (
                            qr is not None
                            and qr.tenant_id == integ.tenant_id
                            and qr.is_active
                        ):
                            mapped_body = qr.payload_text
                    except Exception:
                        pass

                    reply_text, _source = await generate_chat_response(
                        session=session,
                        tenant_id=integ.tenant_id,
                        message=mapped_body,
                        background_tasks=background_tasks,
                    )

                    quick_items = await list_quick_replies_for_tenant(
                        session=session, tenant_id=integ.tenant_id, active_only=True
                    )
                    quick_replies = [
                        {"id": str(q.id), "title": q.title} for q in quick_items
                    ][:10]

                    token = (integ.access_token or "").strip()
                    background_tasks.add_task(
                        send_whatsapp_reply,
                        access_token=token,
                        phone_number_id=str(phone_number_id),
                        to=str(from_number),
                        text=reply_text,
                        quick_replies=quick_replies,
                    )

        return {"status": "ok"}

    # Messenger / Instagram (Graph webhooks)
    if obj in ("page", "instagram"):
        channel_type = "messenger" if obj == "page" else "instagram"

        for entry in entries:
            page_or_ig_id = entry.get("id")
            if not page_or_ig_id:
                continue

            integ = await get_integration_by_type_and_external_id(
                session=session,
                channel_type=channel_type,
                external_id=str(page_or_ig_id),
            )
            if integ is None or not integ.is_active:
                continue

            events = entry.get("messaging") or []
            for ev in events:
                sender = (ev.get("sender") or {}).get("id")
                message = ev.get("message") or {}
                text = message.get("text")
                if not text:
                    # Messenger quick replies arrive as payload.
                    qr = message.get("quick_reply") or {}
                    text = qr.get("payload")

                if not sender or not text:
                    continue

                # If text is a quick reply id, map it to payload_text.
                mapped_text = str(text)
                try:
                    qr_id = int(str(text))
                    qr = await get_quick_reply_by_id(
                        session=session, quick_reply_id=qr_id
                    )
                    if (
                        qr is not None
                        and qr.tenant_id == integ.tenant_id
                        and qr.is_active
                    ):
                        mapped_text = qr.payload_text
                except Exception:
                    pass

                reply_text, _source = await generate_chat_response(
                    session=session,
                    tenant_id=integ.tenant_id,
                    message=mapped_text,
                    background_tasks=background_tasks,
                )

                quick_items = await list_quick_replies_for_tenant(
                    session=session, tenant_id=integ.tenant_id, active_only=True
                )
                quick_replies = [
                    {"id": str(q.id), "title": q.title} for q in quick_items
                ][:10]

                quick_titles = [q["title"] for q in quick_replies]

                # Messenger: send true quick replies. Instagram: fallback to menu text.
                if channel_type == "instagram":
                    reply_text = format_quick_reply_menu_text(reply_text, quick_titles)
                    quick_replies_for_api: list[dict[str, str]] | None = None
                else:
                    quick_replies_for_api = quick_replies

                page_token = (integ.access_token or "").strip()
                background_tasks.add_task(
                    send_page_message_text,
                    page_access_token=page_token,
                    recipient_id=str(sender),
                    text=reply_text,
                    quick_replies=quick_replies_for_api,
                )

        return {"status": "ok"}

    # Unknown object: acknowledge to avoid retries.
    return {"status": "ignored"}
