from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant


async def list_tenants(*, session: AsyncSession, limit: int = 200) -> list[Tenant]:
    result = await session.execute(
        select(Tenant).order_by(Tenant.id.desc()).limit(limit)
    )
    return list(result.scalars().all())


async def create_tenant(
    *,
    session: AsyncSession,
    name: str,
    api_key: str,
    system_prompt: str | None,
    webhook_url: str | None,
    branding_config: dict,
) -> Tenant:
    tenant = Tenant(
        name=name,
        api_key=api_key,
        system_prompt=system_prompt,
        webhook_url=webhook_url,
        branding_config=branding_config or {},
    )
    session.add(tenant)
    await session.commit()
    await session.refresh(tenant)
    return tenant


async def rotate_tenant_api_key(
    *, session: AsyncSession, tenant: Tenant, new_api_key: str
) -> Tenant:
    tenant.api_key = new_api_key
    session.add(tenant)
    await session.commit()
    await session.refresh(tenant)
    return tenant


async def update_tenant_name(
    *, session: AsyncSession, tenant: Tenant, name: str | None
) -> Tenant:
    if name is not None:
        tenant.name = name
    session.add(tenant)
    await session.commit()
    await session.refresh(tenant)
    return tenant


async def delete_tenant(*, session: AsyncSession, tenant: Tenant) -> None:
    await session.delete(tenant)
    await session.commit()


async def get_tenant_by_id(*, session: AsyncSession, tenant_id: int) -> Tenant | None:
    return await session.get(Tenant, tenant_id)


async def get_tenant_by_api_key(
    *, session: AsyncSession, api_key: str
) -> Tenant | None:
    result = await session.execute(select(Tenant).where(Tenant.api_key == api_key))
    return result.scalar_one_or_none()


async def update_tenant_settings(
    *,
    session: AsyncSession,
    tenant: Tenant,
    system_prompt: str | None,
    webhook_url: str | None,
) -> Tenant:
    if system_prompt is not None:
        tenant.system_prompt = system_prompt
    if webhook_url is not None:
        tenant.webhook_url = webhook_url

    session.add(tenant)
    await session.commit()
    await session.refresh(tenant)
    return tenant
