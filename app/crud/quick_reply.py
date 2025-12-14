from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.quick_reply import QuickReply


async def list_quick_replies_for_tenant(
    *, session: AsyncSession, tenant_id: int, active_only: bool = False
) -> list[QuickReply]:
    q = select(QuickReply).where(QuickReply.tenant_id == tenant_id)
    if active_only:
        q = q.where(QuickReply.is_active.is_(True))
    q = q.order_by(QuickReply.sort_order.asc(), QuickReply.id.asc())
    res = await session.execute(q)
    return list(res.scalars().all())


async def get_quick_reply_by_id(
    *, session: AsyncSession, quick_reply_id: int
) -> QuickReply | None:
    return await session.get(QuickReply, quick_reply_id)


async def create_quick_reply(
    *,
    session: AsyncSession,
    tenant_id: int,
    title: str,
    payload_text: str,
    sort_order: int = 0,
    is_active: bool = True,
) -> QuickReply:
    obj = QuickReply(
        tenant_id=tenant_id,
        title=title,
        payload_text=payload_text,
        sort_order=sort_order,
        is_active=is_active,
    )
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return obj


async def update_quick_reply(
    *,
    session: AsyncSession,
    quick_reply: QuickReply,
    title: str | None = None,
    payload_text: str | None = None,
    sort_order: int | None = None,
    is_active: bool | None = None,
) -> QuickReply:
    if title is not None:
        quick_reply.title = title
    if payload_text is not None:
        quick_reply.payload_text = payload_text
    if sort_order is not None:
        quick_reply.sort_order = sort_order
    if is_active is not None:
        quick_reply.is_active = is_active
    session.add(quick_reply)
    await session.commit()
    await session.refresh(quick_reply)
    return quick_reply


async def delete_quick_reply(*, session: AsyncSession, quick_reply: QuickReply) -> None:
    await session.delete(quick_reply)
    await session.commit()


async def delete_all_quick_replies_for_tenant(
    *, session: AsyncSession, tenant_id: int
) -> None:
    await session.execute(delete(QuickReply).where(QuickReply.tenant_id == tenant_id))
    await session.commit()
