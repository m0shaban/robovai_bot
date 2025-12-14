from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lead import Lead


async def create_lead(
    *,
    session: AsyncSession,
    tenant_id: int,
    customer_name: str | None,
    phone_number: str | None,
    summary: str | None,
) -> Lead:
    obj = Lead(
        tenant_id=tenant_id,
        customer_name=customer_name,
        phone_number=phone_number,
        summary=summary,
    )
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return obj


async def list_leads(
    *, session: AsyncSession, tenant_id: int, limit: int = 200
) -> list[Lead]:
    result = await session.execute(
        select(Lead)
        .where(Lead.tenant_id == tenant_id)
        .order_by(Lead.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())
