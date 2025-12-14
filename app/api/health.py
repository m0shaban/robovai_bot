from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import text

from app.db.session import async_session_maker

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    # Basic DB connectivity check
    async with async_session_maker() as session:
        await session.execute(text("SELECT 1"))
    return {"status": "ok"}
