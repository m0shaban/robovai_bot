from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.schemas.chat import ChatSendRequest, ChatSendResponse
from app.services.chat_service import ChatManager
from app.services.lead_service import detect_and_save_lead
from app.crud.tenant import get_tenant_by_api_key

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/send", response_model=ChatSendResponse)
async def send_message(
    payload: ChatSendRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db_session),
) -> ChatSendResponse:
    tenant = await get_tenant_by_api_key(
        session=session, api_key=payload.tenant_api_key
    )
    tenant_id = tenant.id if tenant else None

    # If tenant key invalid, still respond (avoid leaking tenant existence); source=bot.
    if tenant_id is None:
        return ChatSendResponse(response="Invalid tenant_api_key", source="bot")

    manager = ChatManager(session=session)
    result = await manager.process_message(
        tenant_id=tenant_id, user_message=payload.message
    )

    # Fire-and-forget CRM detection after responding.
    background_tasks.add_task(
        detect_and_save_lead, tenant_id=tenant_id, user_message=payload.message
    )

    return ChatSendResponse(response=result.response, source=result.source)
