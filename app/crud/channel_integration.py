from __future__ import annotations

import secrets

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.channel_integration import ChannelIntegration


def generate_verify_token() -> str:
    return secrets.token_urlsafe(24)


async def list_integrations_for_tenant(
    *, session: AsyncSession, tenant_id: int
) -> list[ChannelIntegration]:
    res = await session.execute(
        select(ChannelIntegration)
        .where(ChannelIntegration.tenant_id == tenant_id)
        .order_by(ChannelIntegration.channel_type.asc(), ChannelIntegration.id.asc())
    )
    return list(res.scalars().all())


async def get_integration_by_id(
    *, session: AsyncSession, integration_id: int
) -> ChannelIntegration | None:
    res = await session.execute(
        select(ChannelIntegration).where(ChannelIntegration.id == integration_id)
    )
    return res.scalars().first()


async def get_integration_by_verify_token(
    *, session: AsyncSession, verify_token: str, channel_types: list[str] | None = None
) -> ChannelIntegration | None:
    q = select(ChannelIntegration).where(
        ChannelIntegration.verify_token == verify_token
    )
    if channel_types:
        q = q.where(ChannelIntegration.channel_type.in_(channel_types))
    res = await session.execute(q)
    return res.scalars().first()


async def get_integration_by_type_and_external_id(
    *, session: AsyncSession, channel_type: str, external_id: str
) -> ChannelIntegration | None:
    res = await session.execute(
        select(ChannelIntegration)
        .where(ChannelIntegration.channel_type == channel_type)
        .where(ChannelIntegration.external_id == external_id)
    )
    return res.scalars().first()


async def create_integration(
    *,
    session: AsyncSession,
    tenant_id: int,
    channel_type: str,
    external_id: str | None,
    access_token: str | None,
    verify_token: str | None,
    is_active: bool = True,
) -> ChannelIntegration:
    integ = ChannelIntegration(
        tenant_id=tenant_id,
        channel_type=channel_type,
        external_id=external_id,
        access_token=access_token,
        verify_token=verify_token or generate_verify_token(),
        is_active=is_active,
    )
    session.add(integ)
    await session.commit()
    await session.refresh(integ)
    return integ


async def update_integration(
    *,
    session: AsyncSession,
    integration: ChannelIntegration,
    external_id: str | None = None,
    access_token: str | None = None,
    verify_token: str | None = None,
    is_active: bool | None = None,
) -> ChannelIntegration:
    if external_id is not None:
        integration.external_id = external_id
    if access_token is not None:
        integration.access_token = access_token
    if verify_token is not None:
        integration.verify_token = verify_token
    if is_active is not None:
        integration.is_active = is_active

    await session.commit()
    await session.refresh(integration)
    return integration


async def rotate_verify_token(
    *, session: AsyncSession, integration: ChannelIntegration
) -> ChannelIntegration:
    integration.verify_token = generate_verify_token()
    await session.commit()
    await session.refresh(integration)
    return integration


async def delete_integration(
    *, session: AsyncSession, integration: ChannelIntegration
) -> None:
    await session.delete(integration)
    await session.commit()
