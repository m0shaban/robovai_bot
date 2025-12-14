from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.broadcast import Broadcast, BroadcastStatus


async def create_broadcast(
    *,
    session: AsyncSession,
    tenant_id: int,
    name: str,
    message: str,
    target_channel: str = "all",
) -> Broadcast:
    obj = Broadcast(
        tenant_id=tenant_id,
        name=name,
        message=message,
        target_channel=target_channel,
        status=BroadcastStatus.draft,
    )
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return obj


async def list_broadcasts(
    *, session: AsyncSession, tenant_id: int
) -> list[Broadcast]:
    stmt = (
        select(Broadcast)
        .where(Broadcast.tenant_id == tenant_id)
        .order_by(Broadcast.created_at.desc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_broadcast(
    session: AsyncSession, broadcast_id: int
) -> Broadcast | None:
    return await session.get(Broadcast, broadcast_id)


async def update_broadcast_stats(
    session: AsyncSession, broadcast_id: int, sent: int = 0, failed: int = 0, status: BroadcastStatus | None = None
) -> None:
    obj = await session.get(Broadcast, broadcast_id)
    if not obj:
        return
    
    obj.sent_count += sent
    obj.failed_count += failed
    if status:
        obj.status = status
        
    session.add(obj)
    await session.commit()
