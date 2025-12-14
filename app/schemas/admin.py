from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, Field


class ScriptedResponseCreateRequest(BaseModel):
    tenant_api_key: str = Field(min_length=1)
    trigger_keyword: str = Field(min_length=1, max_length=255)
    response_text: str = Field(min_length=1, max_length=20000)
    is_active: bool = True


class ScriptedResponseCreateResponse(BaseModel):
    id: int
    tenant_id: int
    trigger_keyword: str
    response_text: str
    is_active: bool


class ScriptedResponseUpdateRequest(BaseModel):
    tenant_api_key: str = Field(min_length=1)
    trigger_keyword: str | None = Field(default=None, max_length=255)
    response_text: str | None = Field(default=None, max_length=20000)
    is_active: bool | None = None


class LeadOut(BaseModel):
    id: int
    tenant_id: int
    customer_name: str | None
    phone_number: str | None
    summary: str | None
    created_at: dt.datetime


class TenantSettingsOut(BaseModel):
    tenant_id: int
    system_prompt: str | None
    webhook_url: str | None


class TenantSettingsUpdateRequest(BaseModel):
    tenant_api_key: str = Field(min_length=1)
    system_prompt: str | None = None
    webhook_url: str | None = None


class AdminAuth(BaseModel):
    admin_password: str = Field(min_length=1)


class TenantCreateRequest(BaseModel):
    admin_password: str = Field(min_length=1)
    name: str = Field(min_length=1, max_length=255)
    system_prompt: str | None = None
    webhook_url: str | None = None


class TenantOut(BaseModel):
    id: int
    name: str
    api_key: str
    system_prompt: str | None
    webhook_url: str | None


class TenantRotateKeyRequest(BaseModel):
    admin_password: str = Field(min_length=1)


class TenantUpdateRequest(BaseModel):
    admin_password: str = Field(min_length=1)
    name: str | None = Field(default=None, max_length=255)


class TenantDeleteRequest(BaseModel):
    admin_password: str = Field(min_length=1)


class ChatLogOut(BaseModel):
    id: int
    lead_id: int
    message: str
    sender_type: str
    timestamp: dt.datetime


class ChannelIntegrationOut(BaseModel):
    id: int
    tenant_id: int
    channel_type: str
    external_id: str | None
    is_active: bool
    verify_token: str
    created_at: dt.datetime


class ChannelIntegrationCreateRequest(BaseModel):
    tenant_api_key: str = Field(min_length=1)
    channel_type: str = Field(min_length=1, max_length=32)
    external_id: str | None = Field(default=None, max_length=128)
    access_token: str | None = None
    verify_token: str | None = Field(default=None, max_length=128)
    is_active: bool = True


class ChannelIntegrationUpdateRequest(BaseModel):
    tenant_api_key: str = Field(min_length=1)
    external_id: str | None = Field(default=None, max_length=128)
    access_token: str | None = None
    verify_token: str | None = Field(default=None, max_length=128)
    is_active: bool | None = None


class ChannelIntegrationRotateVerifyTokenRequest(BaseModel):
    tenant_api_key: str = Field(min_length=1)


class QuickReplyOut(BaseModel):
    id: int
    tenant_id: int
    title: str
    payload_text: str
    sort_order: int
    is_active: bool


class QuickReplyCreateRequest(BaseModel):
    tenant_api_key: str = Field(min_length=1)
    title: str = Field(min_length=1, max_length=64)
    payload_text: str = Field(min_length=1, max_length=512)
    sort_order: int = 0
    is_active: bool = True


class QuickReplyUpdateRequest(BaseModel):
    tenant_api_key: str = Field(min_length=1)
    title: str | None = Field(default=None, max_length=64)
    payload_text: str | None = Field(default=None, max_length=512)
    sort_order: int | None = None
    is_active: bool | None = None
