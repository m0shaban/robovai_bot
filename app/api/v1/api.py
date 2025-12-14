from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.routers import admin, chat

api_router = APIRouter(prefix="/v1")
api_router.include_router(chat.router)
api_router.include_router(admin.router)
