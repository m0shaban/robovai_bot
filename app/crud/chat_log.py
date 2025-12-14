from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat_log import ChatLog
from app.models.lead import Lead


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
