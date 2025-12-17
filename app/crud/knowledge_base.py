from __future__ import annotations

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge_base import KnowledgeBase


async def create_kb_item(
    *,
    session: AsyncSession,
    tenant_id: int,
    title: str,
    content: str,
) -> KnowledgeBase:
    obj = KnowledgeBase(
        tenant_id=tenant_id,
        title=title,
        content=content,
    )
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return obj


async def list_kb_items(
    *, session: AsyncSession, tenant_id: int
) -> list[KnowledgeBase]:
    stmt = (
        select(KnowledgeBase)
        .where(KnowledgeBase.tenant_id == tenant_id)
        .order_by(KnowledgeBase.created_at.desc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_kb_item(session: AsyncSession, kb_id: int) -> KnowledgeBase | None:
    return await session.get(KnowledgeBase, kb_id)


async def update_kb_item(
    session: AsyncSession,
    kb_id: int,
    title: str | None = None,
    content: str | None = None,
    is_active: bool | None = None,
) -> KnowledgeBase | None:
    obj = await session.get(KnowledgeBase, kb_id)
    if not obj:
        return None

    if title is not None:
        obj.title = title
    if content is not None:
        obj.content = content
    if is_active is not None:
        obj.is_active = is_active

    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return obj


async def delete_kb_item(session: AsyncSession, kb_id: int) -> None:
    obj = await session.get(KnowledgeBase, kb_id)
    if obj:
        await session.delete(obj)
        await session.commit()


async def search_kb_context(
    session: AsyncSession, tenant_id: int, query: str, limit: int = 5
) -> str:
    """
    Simple retrieval: fetches all active KB items for the tenant.
    In a real production RAG, this would use vector search.
    For now, we concatenate all active items (assuming small scale).
    """
    stmt = (
        select(KnowledgeBase)
        .where(KnowledgeBase.tenant_id == tenant_id)
        .where(KnowledgeBase.is_active == True)
    )
    result = await session.execute(stmt)
    items = result.scalars().all()

    if not items:
        return ""

    # Format as context
    context_parts = ["معلومات مرجعية (Knowledge Base):"]
    for item in items:
        context_parts.append(f"- {item.title}: {item.content}")

    return "\n\n".join(context_parts)
