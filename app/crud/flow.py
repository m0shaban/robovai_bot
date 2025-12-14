from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.flow import Flow


async def create_flow(
    session: AsyncSession,
    tenant_id: int,
    name: str,
    flow_data: dict,
    trigger_keyword: str | None = None,
) -> Flow:
    flow = Flow(
        tenant_id=tenant_id,
        name=name,
        flow_data=flow_data,
        trigger_keyword=trigger_keyword,
    )
    session.add(flow)
    await session.commit()
    await session.refresh(flow)
    return flow


async def get_flow(session: AsyncSession, flow_id: int) -> Flow | None:
    return await session.get(Flow, flow_id)


async def list_flows(session: AsyncSession, tenant_id: int) -> Sequence[Flow]:
    stmt = select(Flow).where(Flow.tenant_id == tenant_id).order_by(Flow.id.desc())
    result = await session.execute(stmt)
    return result.scalars().all()


async def update_flow(
    session: AsyncSession,
    flow_id: int,
    name: str | None = None,
    flow_data: dict | None = None,
    trigger_keyword: str | None = None,
    is_active: bool | None = None,
) -> Flow | None:
    flow = await get_flow(session, flow_id)
    if not flow:
        return None

    if name is not None:
        flow.name = name
    if flow_data is not None:
        flow.flow_data = flow_data
    if trigger_keyword is not None:
        flow.trigger_keyword = trigger_keyword
    if is_active is not None:
        flow.is_active = is_active

    await session.commit()
    await session.refresh(flow)
    return flow


async def delete_flow(session: AsyncSession, flow_id: int) -> bool:
    flow = await get_flow(session, flow_id)
    if not flow:
        return False
    await session.delete(flow)
    await session.commit()
    return True


async def get_flow_by_trigger(
    session: AsyncSession, tenant_id: int, keyword: str
) -> Flow | None:
    # Simple case-insensitive match
    stmt = select(Flow).where(
        Flow.tenant_id == tenant_id,
        Flow.is_active == True,
        Flow.trigger_keyword.ilike(keyword),
    )
    result = await session.execute(stmt)
    return result.scalars().first()
