from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.scripted_response import ScriptedResponse


async def list_active_scripted_responses(
    *, session: AsyncSession, tenant_id: int
) -> list[ScriptedResponse]:
    result = await session.execute(
        select(ScriptedResponse)
        .where(ScriptedResponse.tenant_id == tenant_id)
        .where(ScriptedResponse.is_active.is_(True))
        .order_by(ScriptedResponse.id.asc())
    )
    return list(result.scalars().all())


async def create_scripted_response(
    *,
    session: AsyncSession,
    tenant_id: int,
    trigger_keyword: str,
    response_text: str,
    is_active: bool = True,
) -> ScriptedResponse:
    obj = ScriptedResponse(
        tenant_id=tenant_id,
        trigger_keyword=trigger_keyword,
        response_text=response_text,
        is_active=is_active,
    )
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return obj


async def get_scripted_response_by_id(
    *, session: AsyncSession, scripted_response_id: int
) -> ScriptedResponse | None:
    return await session.get(ScriptedResponse, scripted_response_id)


async def update_scripted_response(
    *,
    session: AsyncSession,
    scripted_response: ScriptedResponse,
    trigger_keyword: str | None = None,
    response_text: str | None = None,
    is_active: bool | None = None,
) -> ScriptedResponse:
    if trigger_keyword is not None:
        scripted_response.trigger_keyword = trigger_keyword
    if response_text is not None:
        scripted_response.response_text = response_text
    if is_active is not None:
        scripted_response.is_active = is_active
    session.add(scripted_response)
    await session.commit()
    await session.refresh(scripted_response)
    return scripted_response


async def delete_scripted_response(
    *, session: AsyncSession, scripted_response: ScriptedResponse
) -> None:
    await session.delete(scripted_response)
    await session.commit()
