from __future__ import annotations

from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.chat_service import ChatManager
from app.services.lead_service import detect_and_save_lead


async def generate_chat_response(
    *,
    session: AsyncSession,
    tenant_id: int,
    message: str,
    background_tasks: BackgroundTasks | None = None,
) -> tuple[str, str]:
    """Runs the unified chatbot logic and optionally triggers lead detection."""

    manager = ChatManager(session=session)
    result = await manager.process_message(tenant_id=tenant_id, user_message=message)

    if background_tasks is not None:
        background_tasks.add_task(
            detect_and_save_lead, tenant_id=tenant_id, user_message=message
        )

    return result.response, result.source
