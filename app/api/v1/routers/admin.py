from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.core.config import admin_auth_enabled, settings
from app.crud.chat_log import list_chat_logs_for_tenant
from app.crud.lead import list_leads
from app.crud.scripted_response import (
    create_scripted_response,
    delete_scripted_response,
    get_scripted_response_by_id,
    update_scripted_response,
)
from app.crud.quick_reply import (
    create_quick_reply,
    delete_quick_reply,
    get_quick_reply_by_id,
    list_quick_replies_for_tenant,
    update_quick_reply,
)
from app.crud.channel_integration import (
    create_integration,
    delete_integration,
    get_integration_by_id,
    list_integrations_for_tenant,
    rotate_verify_token,
    update_integration,
)
from app.crud.tenant import (
    create_tenant,
    delete_tenant,
    get_tenant_by_api_key,
    get_tenant_by_id,
    list_tenants,
    rotate_tenant_api_key,
    update_tenant_name,
    update_tenant_settings,
)
from app.schemas.admin import (
    ChatLogOut,
    ChannelIntegrationCreateRequest,
    ChannelIntegrationOut,
    ChannelIntegrationRotateVerifyTokenRequest,
    ChannelIntegrationUpdateRequest,
    LeadOut,
    TenantCreateRequest,
    TenantOut,
    TenantRotateKeyRequest,
    TenantUpdateRequest,
    TenantDeleteRequest,
    ScriptedResponseCreateRequest,
    ScriptedResponseCreateResponse,
    ScriptedResponseUpdateRequest,
    TenantSettingsOut,
    TenantSettingsUpdateRequest,
    QuickReplyOut,
    QuickReplyCreateRequest,
    QuickReplyUpdateRequest,
)

router = APIRouter(prefix="/admin", tags=["admin"])


def _require_admin_password(admin_password: str) -> None:
    # If ADMIN_PASSWORD is not configured, allow for local/dev.
    if not admin_auth_enabled():
        return
    if admin_password != settings.admin_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin_password"
        )


@router.post("/rules", response_model=ScriptedResponseCreateResponse)
async def add_rule(
    payload: ScriptedResponseCreateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> ScriptedResponseCreateResponse:
    tenant = await get_tenant_by_api_key(
        session=session, api_key=payload.tenant_api_key
    )
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid tenant_api_key"
        )

    rule = await create_scripted_response(
        session=session,
        tenant_id=tenant.id,
        trigger_keyword=payload.trigger_keyword,
        response_text=payload.response_text,
        is_active=payload.is_active,
    )

    return ScriptedResponseCreateResponse(
        id=rule.id,
        tenant_id=rule.tenant_id,
        trigger_keyword=rule.trigger_keyword,
        response_text=rule.response_text,
        is_active=rule.is_active,
    )


@router.put("/rules/{rule_id}", response_model=ScriptedResponseCreateResponse)
async def update_rule(
    rule_id: int,
    payload: ScriptedResponseUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> ScriptedResponseCreateResponse:
    tenant = await get_tenant_by_api_key(
        session=session, api_key=payload.tenant_api_key
    )
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid tenant_api_key"
        )

    rule = await get_scripted_response_by_id(
        session=session, scripted_response_id=rule_id
    )
    if rule is None or rule.tenant_id != tenant.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found"
        )

    rule = await update_scripted_response(
        session=session,
        scripted_response=rule,
        trigger_keyword=payload.trigger_keyword,
        response_text=payload.response_text,
        is_active=payload.is_active,
    )

    return ScriptedResponseCreateResponse(
        id=rule.id,
        tenant_id=rule.tenant_id,
        trigger_keyword=rule.trigger_keyword,
        response_text=rule.response_text,
        is_active=rule.is_active,
    )


@router.delete(
    "/rules/{rule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def delete_rule(
    rule_id: int,
    tenant_api_key: str,
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    tenant = await get_tenant_by_api_key(session=session, api_key=tenant_api_key)
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid tenant_api_key"
        )

    rule = await get_scripted_response_by_id(
        session=session, scripted_response_id=rule_id
    )
    if rule is None or rule.tenant_id != tenant.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found"
        )

    await delete_scripted_response(session=session, scripted_response=rule)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/quick-replies", response_model=list[QuickReplyOut])
async def list_quick_replies(
    tenant_api_key: str,
    session: AsyncSession = Depends(get_db_session),
) -> list[QuickReplyOut]:
    tenant = await get_tenant_by_api_key(session=session, api_key=tenant_api_key)
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid tenant_api_key"
        )

    items = await list_quick_replies_for_tenant(session=session, tenant_id=tenant.id)
    return [
        QuickReplyOut(
            id=q.id,
            tenant_id=q.tenant_id,
            title=q.title,
            payload_text=q.payload_text,
            sort_order=q.sort_order,
            is_active=q.is_active,
        )
        for q in items
    ]


@router.post("/quick-replies", response_model=QuickReplyOut)
async def add_quick_reply(
    payload: QuickReplyCreateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> QuickReplyOut:
    tenant = await get_tenant_by_api_key(
        session=session, api_key=payload.tenant_api_key
    )
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid tenant_api_key"
        )

    obj = await create_quick_reply(
        session=session,
        tenant_id=tenant.id,
        title=payload.title,
        payload_text=payload.payload_text,
        sort_order=payload.sort_order,
        is_active=payload.is_active,
    )
    return QuickReplyOut(
        id=obj.id,
        tenant_id=obj.tenant_id,
        title=obj.title,
        payload_text=obj.payload_text,
        sort_order=obj.sort_order,
        is_active=obj.is_active,
    )


@router.put("/quick-replies/{quick_reply_id}", response_model=QuickReplyOut)
async def update_quick_reply_item(
    quick_reply_id: int,
    payload: QuickReplyUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> QuickReplyOut:
    tenant = await get_tenant_by_api_key(
        session=session, api_key=payload.tenant_api_key
    )
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid tenant_api_key"
        )
    obj = await get_quick_reply_by_id(session=session, quick_reply_id=quick_reply_id)
    if obj is None or obj.tenant_id != tenant.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Quick reply not found"
        )

    obj = await update_quick_reply(
        session=session,
        quick_reply=obj,
        title=payload.title,
        payload_text=payload.payload_text,
        sort_order=payload.sort_order,
        is_active=payload.is_active,
    )
    return QuickReplyOut(
        id=obj.id,
        tenant_id=obj.tenant_id,
        title=obj.title,
        payload_text=obj.payload_text,
        sort_order=obj.sort_order,
        is_active=obj.is_active,
    )


@router.delete(
    "/quick-replies/{quick_reply_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def delete_quick_reply_item(
    quick_reply_id: int,
    tenant_api_key: str,
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    tenant = await get_tenant_by_api_key(session=session, api_key=tenant_api_key)
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid tenant_api_key"
        )
    obj = await get_quick_reply_by_id(session=session, quick_reply_id=quick_reply_id)
    if obj is None or obj.tenant_id != tenant.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Quick reply not found"
        )

    await delete_quick_reply(session=session, quick_reply=obj)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/leads", response_model=list[LeadOut])
async def get_leads(
    tenant_api_key: str,
    session: AsyncSession = Depends(get_db_session),
) -> list[LeadOut]:
    tenant = await get_tenant_by_api_key(session=session, api_key=tenant_api_key)
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid tenant_api_key"
        )

    leads = await list_leads(session=session, tenant_id=tenant.id)
    return [
        LeadOut(
            id=l.id,
            tenant_id=l.tenant_id,
            customer_name=l.customer_name,
            phone_number=l.phone_number,
            summary=l.summary,
            created_at=l.created_at,
        )
        for l in leads
    ]


@router.get("/settings", response_model=TenantSettingsOut)
async def get_settings(
    tenant_api_key: str,
    session: AsyncSession = Depends(get_db_session),
) -> TenantSettingsOut:
    tenant = await get_tenant_by_api_key(session=session, api_key=tenant_api_key)
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid tenant_api_key"
        )

    return TenantSettingsOut(
        tenant_id=tenant.id,
        system_prompt=tenant.system_prompt,
        webhook_url=tenant.webhook_url,
    )


@router.put("/settings", response_model=TenantSettingsOut)
async def update_settings(
    payload: TenantSettingsUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> TenantSettingsOut:
    tenant = await get_tenant_by_api_key(
        session=session, api_key=payload.tenant_api_key
    )
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid tenant_api_key"
        )

    tenant = await update_tenant_settings(
        session=session,
        tenant=tenant,
        system_prompt=payload.system_prompt,
        webhook_url=payload.webhook_url,
    )

    return TenantSettingsOut(
        tenant_id=tenant.id,
        system_prompt=tenant.system_prompt,
        webhook_url=tenant.webhook_url,
    )


@router.get("/tenants", response_model=list[TenantOut])
async def admin_list_tenants(
    admin_password: str,
    session: AsyncSession = Depends(get_db_session),
) -> list[TenantOut]:
    _require_admin_password(admin_password)
    tenants = await list_tenants(session=session)
    return [
        TenantOut(
            id=t.id,
            name=t.name,
            api_key=t.api_key,
            system_prompt=t.system_prompt,
            webhook_url=t.webhook_url,
        )
        for t in tenants
    ]


@router.post("/tenants", response_model=TenantOut)
async def admin_create_tenant(
    payload: TenantCreateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> TenantOut:
    _require_admin_password(payload.admin_password)
    api_key = secrets.token_urlsafe(24)

    t = await create_tenant(
        session=session,
        name=payload.name,
        api_key=api_key,
        system_prompt=payload.system_prompt,
        webhook_url=payload.webhook_url,
        branding_config={},
    )
    return TenantOut(
        id=t.id,
        name=t.name,
        api_key=t.api_key,
        system_prompt=t.system_prompt,
        webhook_url=t.webhook_url,
    )


@router.post("/tenants/{tenant_id}/rotate-key", response_model=TenantOut)
async def admin_rotate_tenant_key(
    tenant_id: int,
    payload: TenantRotateKeyRequest,
    session: AsyncSession = Depends(get_db_session),
) -> TenantOut:
    _require_admin_password(payload.admin_password)
    tenant = await get_tenant_by_id(session=session, tenant_id=tenant_id)
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found"
        )

    new_key = secrets.token_urlsafe(24)
    tenant = await rotate_tenant_api_key(
        session=session, tenant=tenant, new_api_key=new_key
    )
    return TenantOut(
        id=tenant.id,
        name=tenant.name,
        api_key=tenant.api_key,
        system_prompt=tenant.system_prompt,
        webhook_url=tenant.webhook_url,
    )


@router.put("/tenants/{tenant_id}", response_model=TenantOut)
async def admin_update_tenant(
    tenant_id: int,
    payload: TenantUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> TenantOut:
    _require_admin_password(payload.admin_password)
    tenant = await get_tenant_by_id(session=session, tenant_id=tenant_id)
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found"
        )

    tenant = await update_tenant_name(session=session, tenant=tenant, name=payload.name)

    return TenantOut(
        id=tenant.id,
        name=tenant.name,
        api_key=tenant.api_key,
        system_prompt=tenant.system_prompt,
        webhook_url=tenant.webhook_url,
    )


@router.delete(
    "/tenants/{tenant_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def admin_delete_tenant(
    tenant_id: int,
    payload: TenantDeleteRequest,
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    _require_admin_password(payload.admin_password)
    tenant = await get_tenant_by_id(session=session, tenant_id=tenant_id)
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found"
        )

    await delete_tenant(session=session, tenant=tenant)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/chatlogs", response_model=list[ChatLogOut])
async def get_chatlogs(
    tenant_api_key: str,
    limit: int = 200,
    session: AsyncSession = Depends(get_db_session),
) -> list[ChatLogOut]:
    tenant = await get_tenant_by_api_key(session=session, api_key=tenant_api_key)
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid tenant_api_key"
        )

    logs = await list_chat_logs_for_tenant(
        session=session, tenant_id=tenant.id, limit=limit
    )
    return [
        ChatLogOut(
            id=l.id,
            lead_id=l.lead_id,
            message=l.message,
            sender_type=str(l.sender_type),
            timestamp=l.timestamp,
        )
        for l in logs
    ]


@router.get("/integrations", response_model=list[ChannelIntegrationOut])
async def list_channel_integrations(
    tenant_api_key: str,
    session: AsyncSession = Depends(get_db_session),
) -> list[ChannelIntegrationOut]:
    tenant = await get_tenant_by_api_key(session=session, api_key=tenant_api_key)
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid tenant_api_key"
        )

    items = await list_integrations_for_tenant(session=session, tenant_id=tenant.id)
    return [
        ChannelIntegrationOut(
            id=i.id,
            tenant_id=i.tenant_id,
            channel_type=i.channel_type,
            external_id=i.external_id,
            is_active=i.is_active,
            verify_token=i.verify_token,
            created_at=i.created_at,
        )
        for i in items
    ]


@router.post("/integrations", response_model=ChannelIntegrationOut)
async def create_channel_integration(
    payload: ChannelIntegrationCreateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> ChannelIntegrationOut:
    tenant = await get_tenant_by_api_key(
        session=session, api_key=payload.tenant_api_key
    )
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid tenant_api_key"
        )

    integ = await create_integration(
        session=session,
        tenant_id=tenant.id,
        channel_type=payload.channel_type.strip().lower(),
        external_id=(payload.external_id.strip() if payload.external_id else None),
        access_token=(payload.access_token.strip() if payload.access_token else None),
        verify_token=(payload.verify_token.strip() if payload.verify_token else None),
        is_active=payload.is_active,
    )

    return ChannelIntegrationOut(
        id=integ.id,
        tenant_id=integ.tenant_id,
        channel_type=integ.channel_type,
        external_id=integ.external_id,
        is_active=integ.is_active,
        verify_token=integ.verify_token,
        created_at=integ.created_at,
    )


@router.put("/integrations/{integration_id}", response_model=ChannelIntegrationOut)
async def update_channel_integration(
    integration_id: int,
    payload: ChannelIntegrationUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> ChannelIntegrationOut:
    tenant = await get_tenant_by_api_key(
        session=session, api_key=payload.tenant_api_key
    )
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid tenant_api_key"
        )

    integ = await get_integration_by_id(session=session, integration_id=integration_id)
    if integ is None or integ.tenant_id != tenant.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Integration not found"
        )

    integ = await update_integration(
        session=session,
        integration=integ,
        external_id=(
            payload.external_id.strip() if payload.external_id is not None else None
        ),
        access_token=(
            payload.access_token.strip() if payload.access_token is not None else None
        ),
        verify_token=(
            payload.verify_token.strip() if payload.verify_token is not None else None
        ),
        is_active=payload.is_active,
    )

    return ChannelIntegrationOut(
        id=integ.id,
        tenant_id=integ.tenant_id,
        channel_type=integ.channel_type,
        external_id=integ.external_id,
        is_active=integ.is_active,
        verify_token=integ.verify_token,
        created_at=integ.created_at,
    )


@router.post(
    "/integrations/{integration_id}/rotate-verify-token",
    response_model=ChannelIntegrationOut,
)
async def rotate_channel_integration_verify_token(
    integration_id: int,
    payload: ChannelIntegrationRotateVerifyTokenRequest,
    session: AsyncSession = Depends(get_db_session),
) -> ChannelIntegrationOut:
    tenant = await get_tenant_by_api_key(
        session=session, api_key=payload.tenant_api_key
    )
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid tenant_api_key"
        )

    integ = await get_integration_by_id(session=session, integration_id=integration_id)
    if integ is None or integ.tenant_id != tenant.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Integration not found"
        )

    integ = await rotate_verify_token(session=session, integration=integ)
    return ChannelIntegrationOut(
        id=integ.id,
        tenant_id=integ.tenant_id,
        channel_type=integ.channel_type,
        external_id=integ.external_id,
        is_active=integ.is_active,
        verify_token=integ.verify_token,
        created_at=integ.created_at,
    )


@router.delete(
    "/integrations/{integration_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def delete_channel_integration(
    integration_id: int,
    tenant_api_key: str,
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    tenant = await get_tenant_by_api_key(session=session, api_key=tenant_api_key)
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid tenant_api_key"
        )

    integ = await get_integration_by_id(session=session, integration_id=integration_id)
    if integ is None or integ.tenant_id != tenant.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Integration not found"
        )

    await delete_integration(session=session, integration=integ)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
