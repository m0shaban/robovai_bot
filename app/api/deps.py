from __future__ import annotations

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.tenant import get_tenant_by_api_key
from app.db.session import get_session


async def get_db_session(session: AsyncSession = Depends(get_session)) -> AsyncSession:
    return session


async def get_tenant_id_from_api_key(
    tenant_api_key: str,
    session: AsyncSession = Depends(get_db_session),
) -> int:
    tenant = await get_tenant_by_api_key(session=session, api_key=tenant_api_key)
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid tenant_api_key",
        )
    return tenant.id
