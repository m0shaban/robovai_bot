from __future__ import annotations

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat_log import ChatLog, SenderType
from app.models.lead import Lead


async def create_chat_log(
    session: AsyncSession,
    lead_id: int,
    message: str,
    sender_type: SenderType,
) -> ChatLog:
    obj = ChatLog(
        lead_id=lead_id,
        message=message,
        sender_type=sender_type,
    )
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return obj


async def list_chat_logs_for_tenant(
    *,
    session: AsyncSession,
    tenant_id: int,
    limit: int = 200,
) -> list[ChatLog]:
    # Join leads to enforce tenant scoping
    stmt = (
        select(ChatLog)
        .join(Lead, Lead.id == ChatLog.lead_id)
        .where(Lead.tenant_id == tenant_id)
        .order_by(ChatLog.timestamp.desc())
        .limit(limit)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_chat_history_for_lead(
    session: AsyncSession,
    lead_id: int,
) -> list[ChatLog]:
    stmt = (
        select(ChatLog)
        .where(ChatLog.lead_id == lead_id)
        .order_by(ChatLog.timestamp.asc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_inbox_conversations(
    session: AsyncSession,
    tenant_id: int,
    limit: int = 50
) -> list[tuple[Lead, ChatLog]]:
    """
    Returns a list of (Lead, latest_ChatLog) tuples, ordered by latest message.
    """
    # Subquery to find the latest timestamp for each lead
    subq = (
        select(
            ChatLog.lead_id,
            func.max(ChatLog.timestamp).label("max_ts")
        )
        .group_by(ChatLog.lead_id)
        .subquery()
    )

    # Join Lead -> subq -> ChatLog to get the full details of the latest message
    stmt = (
        select(Lead, ChatLog)
        .join(subq, Lead.id == subq.c.lead_id)
        .join(ChatLog, (ChatLog.lead_id == Lead.id) & (ChatLog.timestamp == subq.c.max_ts))
        .where(Lead.tenant_id == tenant_id)
        .order_by(desc(subq.c.max_ts))
        .limit(limit)
    )
    
    result = await session.execute(stmt)
    return list(result.all())
