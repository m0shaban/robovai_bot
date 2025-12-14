from __future__ import annotations

import secrets
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.core.config import admin_auth_enabled, settings
from app.crud.tenant import (
    create_tenant,
    delete_tenant,
    get_tenant_by_id,
    get_tenant_by_api_key,
    list_tenants,
    rotate_tenant_api_key,
    update_tenant_name,
    update_tenant_settings,
)
from app.crud.channel_integration import (
    create_integration,
    delete_integration,
    get_integration_by_id,
    list_integrations_for_tenant,
    rotate_verify_token,
    update_integration,
)
from app.crud.quick_reply import (
    create_quick_reply,
    delete_quick_reply,
    get_quick_reply_by_id,
    list_quick_replies_for_tenant,
    update_quick_reply,
)
from app.crud.scripted_response import (
    create_scripted_response,
    delete_scripted_response,
    get_scripted_response_by_id,
    list_active_scripted_responses,
    update_scripted_response,
)
from app.crud.lead import list_leads
from app.crud.chat_log import list_chat_logs_for_tenant

# Templates directory (app/templates)
TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

router = APIRouter(prefix="/ui", tags=["ui"])


def _require_admin_password(admin_password: str) -> None:
    if not admin_auth_enabled():
        return
    if admin_password != settings.admin_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin_password"
        )


@router.get("/", response_class=HTMLResponse)
async def ui_root(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse | RedirectResponse:
    """Show onboarding for first-time users, otherwise go to tenants page"""
    tenants = await list_tenants(session=session)
    if not tenants:
        return templates.TemplateResponse("onboarding.html", {"request": request})
    return RedirectResponse(url="/ui/tenants", status_code=status.HTTP_302_FOUND)


@router.get("/tenants", response_class=HTMLResponse)
async def tenants_page(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    tenants = await list_tenants(session=session)
    return templates.TemplateResponse(
        "tenants.html",
        {"request": request, "tenants": tenants, "admin_protected": admin_auth_enabled()},
    )


@router.get("/tenants/rows", response_class=HTMLResponse)
async def tenants_rows(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    tenants = await list_tenants(session=session)
    return templates.TemplateResponse(
        "_tenant_rows.html",
        {"request": request, "tenants": tenants},
    )


@router.post("/tenants", response_class=HTMLResponse)
async def create_tenant_web(
    request: Request,
    name: str,
    admin_password: str = "",
    system_prompt: str | None = None,
    webhook_url: str | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    _require_admin_password(admin_password)
    api_key = secrets.token_urlsafe(32)
    await create_tenant(
        session=session,
        name=name,
        api_key=api_key,
        system_prompt=system_prompt,
        webhook_url=webhook_url,
        branding_config={},
    )
    tenants = await list_tenants(session=session)
    return templates.TemplateResponse(
        "_tenant_rows.html", {"request": request, "tenants": tenants}, status_code=status.HTTP_201_CREATED
    )


@router.post("/tenants/{tenant_id}/rotate", response_class=HTMLResponse)
async def rotate_tenant_key(
    request: Request,
    tenant_id: int,
    admin_password: str = "",
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    _require_admin_password(admin_password)
    tenant = await get_tenant_by_id(session=session, tenant_id=tenant_id)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    await rotate_tenant_api_key(session=session, tenant=tenant, new_api_key=secrets.token_urlsafe(32))
    tenants = await list_tenants(session=session)
    return templates.TemplateResponse(
        "_tenant_rows.html", {"request": request, "tenants": tenants}, status_code=status.HTTP_200_OK
    )


@router.post("/tenants/{tenant_id}/update", response_class=HTMLResponse)
async def update_tenant_web(
    request: Request,
    tenant_id: int,
    admin_password: str = "",
    name: str | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    _require_admin_password(admin_password)
    tenant = await get_tenant_by_id(session=session, tenant_id=tenant_id)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    await update_tenant_name(session=session, tenant=tenant, name=name)
    tenants = await list_tenants(session=session)
    return templates.TemplateResponse(
        "_tenant_rows.html", {"request": request, "tenants": tenants}, status_code=status.HTTP_200_OK
    )


@router.post("/tenants/{tenant_id}/delete", response_class=HTMLResponse)
async def delete_tenant_web(
    request: Request,
    tenant_id: int,
    admin_password: str = "",
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    _require_admin_password(admin_password)
    tenant = await get_tenant_by_id(session=session, tenant_id=tenant_id)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    await delete_tenant(session=session, tenant=tenant)
    tenants = await list_tenants(session=session)
    return templates.TemplateResponse(
        "_tenant_rows.html", {"request": request, "tenants": tenants}, status_code=status.HTTP_200_OK
    )


# ============ CHANNELS ============
@router.get("/channels", response_class=HTMLResponse)
async def channels_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("channels.html", {"request": request})


@router.get("/channels/rows", response_class=HTMLResponse)
async def channels_rows(
    request: Request,
    tenant_api_key: str,
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    tenant = await get_tenant_by_api_key(session=session, api_key=tenant_api_key)
    if not tenant:
        return templates.TemplateResponse(
            "_channel_rows.html", {"request": request, "channels": [], "error": "Invalid tenant_api_key"}
        )
    channels = await list_integrations_for_tenant(session=session, tenant_id=tenant.id)
    return templates.TemplateResponse("_channel_rows.html", {"request": request, "channels": channels})


@router.post("/channels", response_class=HTMLResponse)
async def create_channel_web(
    request: Request,
    tenant_api_key: str,
    channel_type: str,
    external_id: str = "",
    access_token: str = "",
    verify_token: str = "",
    is_active: bool = True,
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    tenant = await get_tenant_by_api_key(session=session, api_key=tenant_api_key)
    if not tenant:
        return templates.TemplateResponse(
            "_channel_rows.html", {"request": request, "channels": [], "error": "Invalid tenant_api_key"}
        )
    await create_integration(
        session=session,
        tenant_id=tenant.id,
        channel_type=channel_type.strip().lower(),
        external_id=external_id.strip() or None,
        access_token=access_token.strip() or None,
        verify_token=verify_token.strip() or None,
        is_active=is_active,
    )
    channels = await list_integrations_for_tenant(session=session, tenant_id=tenant.id)
    return templates.TemplateResponse(
        "_channel_rows.html", {"request": request, "channels": channels}, status_code=status.HTTP_201_CREATED
    )


@router.post("/channels/{channel_id}/delete", response_class=HTMLResponse)
async def delete_channel_web(
    request: Request,
    channel_id: int,
    tenant_api_key: str,
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    tenant = await get_tenant_by_api_key(session=session, api_key=tenant_api_key)
    if not tenant:
        return templates.TemplateResponse(
            "_channel_rows.html", {"request": request, "channels": [], "error": "Invalid tenant_api_key"}
        )
    channel = await get_integration_by_id(session=session, integration_id=channel_id)
    if channel and channel.tenant_id == tenant.id:
        await delete_integration(session=session, integration=channel)
    channels = await list_integrations_for_tenant(session=session, tenant_id=tenant.id)
    return templates.TemplateResponse("_channel_rows.html", {"request": request, "channels": channels})


# ============ QUICK REPLIES ============
@router.get("/quick-replies", response_class=HTMLResponse)
async def quick_replies_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("quick_replies.html", {"request": request})


@router.get("/quick-replies/rows", response_class=HTMLResponse)
async def quick_replies_rows(
    request: Request,
    tenant_api_key: str,
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    tenant = await get_tenant_by_api_key(session=session, api_key=tenant_api_key)
    if not tenant:
        return templates.TemplateResponse(
            "_quick_reply_rows.html", {"request": request, "replies": [], "error": "Invalid tenant_api_key"}
        )
    replies = await list_quick_replies_for_tenant(session=session, tenant_id=tenant.id)
    return templates.TemplateResponse("_quick_reply_rows.html", {"request": request, "replies": replies})


@router.post("/quick-replies", response_class=HTMLResponse)
async def create_quick_reply_web(
    request: Request,
    tenant_api_key: str,
    title: str,
    payload_text: str,
    sort_order: int = 0,
    is_active: bool = True,
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    tenant = await get_tenant_by_api_key(session=session, api_key=tenant_api_key)
    if not tenant:
        return templates.TemplateResponse(
            "_quick_reply_rows.html", {"request": request, "replies": [], "error": "Invalid tenant_api_key"}
        )
    await create_quick_reply(
        session=session,
        tenant_id=tenant.id,
        title=title,
        payload_text=payload_text,
        sort_order=sort_order,
        is_active=is_active,
    )
    replies = await list_quick_replies_for_tenant(session=session, tenant_id=tenant.id)
    return templates.TemplateResponse(
        "_quick_reply_rows.html", {"request": request, "replies": replies}, status_code=status.HTTP_201_CREATED
    )


@router.post("/quick-replies/{reply_id}/delete", response_class=HTMLResponse)
async def delete_quick_reply_web(
    request: Request,
    reply_id: int,
    tenant_api_key: str,
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    tenant = await get_tenant_by_api_key(session=session, api_key=tenant_api_key)
    if not tenant:
        return templates.TemplateResponse(
            "_quick_reply_rows.html", {"request": request, "replies": [], "error": "Invalid tenant_api_key"}
        )
    reply = await get_quick_reply_by_id(session=session, quick_reply_id=reply_id)
    if reply and reply.tenant_id == tenant.id:
        await delete_quick_reply(session=session, quick_reply=reply)
    replies = await list_quick_replies_for_tenant(session=session, tenant_id=tenant.id)
    return templates.TemplateResponse("_quick_reply_rows.html", {"request": request, "replies": replies})


# ============ RULES (Scripted Responses) ============
@router.get("/rules", response_class=HTMLResponse)
async def rules_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("rules.html", {"request": request})


@router.get("/rules/rows", response_class=HTMLResponse)
async def rules_rows(
    request: Request,
    tenant_api_key: str,
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    tenant = await get_tenant_by_api_key(session=session, api_key=tenant_api_key)
    if not tenant:
        return templates.TemplateResponse(
            "_rule_rows.html", {"request": request, "rules": [], "error": "Invalid tenant_api_key"}
        )
    rules = await list_active_scripted_responses(session=session, tenant_id=tenant.id)
    return templates.TemplateResponse("_rule_rows.html", {"request": request, "rules": rules})


@router.post("/rules", response_class=HTMLResponse)
async def create_rule_web(
    request: Request,
    tenant_api_key: str,
    trigger_keyword: str,
    response_text: str,
    is_active: bool = True,
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    tenant = await get_tenant_by_api_key(session=session, api_key=tenant_api_key)
    if not tenant:
        return templates.TemplateResponse(
            "_rule_rows.html", {"request": request, "rules": [], "error": "Invalid tenant_api_key"}
        )
    await create_scripted_response(
        session=session,
        tenant_id=tenant.id,
        trigger_keyword=trigger_keyword,
        response_text=response_text,
        is_active=is_active,
    )
    rules = await list_active_scripted_responses(session=session, tenant_id=tenant.id)
    return templates.TemplateResponse(
        "_rule_rows.html", {"request": request, "rules": rules}, status_code=status.HTTP_201_CREATED
    )


@router.post("/rules/{rule_id}/delete", response_class=HTMLResponse)
async def delete_rule_web(
    request: Request,
    rule_id: int,
    tenant_api_key: str,
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    tenant = await get_tenant_by_api_key(session=session, api_key=tenant_api_key)
    if not tenant:
        return templates.TemplateResponse(
            "_rule_rows.html", {"request": request, "rules": [], "error": "Invalid tenant_api_key"}
        )
    rule = await get_scripted_response_by_id(session=session, scripted_response_id=rule_id)
    if rule and rule.tenant_id == tenant.id:
        await delete_scripted_response(session=session, scripted_response=rule)
    rules = await list_active_scripted_responses(session=session, tenant_id=tenant.id)
    return templates.TemplateResponse("_rule_rows.html", {"request": request, "rules": rules})


# ============ LEADS ============
@router.get("/leads", response_class=HTMLResponse)
async def leads_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("leads.html", {"request": request})


@router.get("/leads/rows", response_class=HTMLResponse)
async def leads_rows(
    request: Request,
    tenant_api_key: str,
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    tenant = await get_tenant_by_api_key(session=session, api_key=tenant_api_key)
    if not tenant:
        return templates.TemplateResponse(
            "_lead_rows.html", {"request": request, "leads": [], "error": "Invalid tenant_api_key"}
        )
    leads = await list_leads(session=session, tenant_id=tenant.id)
    return templates.TemplateResponse("_lead_rows.html", {"request": request, "leads": leads})


# ============ CHAT LOGS ============
@router.get("/chatlogs", response_class=HTMLResponse)
async def chatlogs_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("chatlogs.html", {"request": request})


@router.get("/chatlogs/rows", response_class=HTMLResponse)
async def chatlogs_rows(
    request: Request,
    tenant_api_key: str,
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    tenant = await get_tenant_by_api_key(session=session, api_key=tenant_api_key)
    if not tenant:
        return templates.TemplateResponse(
            "_chatlog_rows.html", {"request": request, "logs": [], "error": "Invalid tenant_api_key"}
        )
    logs = await list_chat_logs_for_tenant(session=session, tenant_id=tenant.id, limit=200)
    return templates.TemplateResponse("_chatlog_rows.html", {"request": request, "logs": logs})


# ============ SETTINGS ============
@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("settings.html", {"request": request})


@router.get("/settings/data", response_class=HTMLResponse)
async def settings_data(
    request: Request,
    tenant_api_key: str,
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    tenant = await get_tenant_by_api_key(session=session, api_key=tenant_api_key)
    if not tenant:
        return templates.TemplateResponse(
            "_settings_form.html",
            {
                "request": request,
                "tenant": None,
                "error": "Invalid tenant_api_key",
            },
        )
    return templates.TemplateResponse("_settings_form.html", {"request": request, "tenant": tenant})


@router.post("/settings/update", response_class=HTMLResponse)
async def update_settings_web(
    request: Request,
    tenant_api_key: str,
    system_prompt: str = "",
    webhook_url: str = "",
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    tenant = await get_tenant_by_api_key(session=session, api_key=tenant_api_key)
    if not tenant:
        return templates.TemplateResponse(
            "_settings_form.html",
            {
                "request": request,
                "tenant": None,
                "error": "Invalid tenant_api_key",
            },
        )
    await update_tenant_settings(
        session=session,
        tenant=tenant,
        system_prompt=system_prompt or None,
        webhook_url=webhook_url or None,
    )
    tenant = await get_tenant_by_id(session=session, tenant_id=tenant.id)
    return templates.TemplateResponse(
        "_settings_form.html",
        {"request": request, "tenant": tenant, "success": "Settings updated successfully"},
    )
