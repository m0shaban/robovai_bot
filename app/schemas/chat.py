from __future__ import annotations

from pydantic import BaseModel, Field


class ChatSendRequest(BaseModel):
    tenant_api_key: str = Field(min_length=1)
    message: str = Field(min_length=1, max_length=8000)


class ChatSendResponse(BaseModel):
    response: str
    source: str  # "bot" | "ai"
