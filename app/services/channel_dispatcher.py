from __future__ import annotations

from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.chat_service import ChatManager
from app.services.lead_service import detect_and_save_lead
from app.crud.lead import get_lead_by_phone, create_lead


async def generate_chat_response(
    *,
    session: AsyncSession,
    tenant_id: int,
    message: str,
    sender_id: str | None = None,
    background_tasks: BackgroundTasks | None = None,
) -> tuple[str, str]:
    """Runs the unified chatbot logic and optionally triggers lead detection."""

    # Try to find or create a lead to track flow state
    lead = None
    if sender_id:
        # Assuming sender_id is phone number for now
        lead = await get_lead_by_phone(session, tenant_id, sender_id)
        if not lead:
            # Create a basic lead so we can track flow state immediately
            lead = await create_lead(
                session=session,
                tenant_id=tenant_id,
                phone_number=sender_id,
                customer_name=None,
                summary=None,
            )

    manager = ChatManager(session=session)
    result = await manager.process_message(
        tenant_id=tenant_id, user_message=message, lead=lead
    )

    if background_tasks is not None:
        background_tasks.add_task(
            detect_and_save_lead,
            tenant_id=tenant_id,
            user_message=message,
            sender_id=sender_id,
        )

    return result.response, result.source
