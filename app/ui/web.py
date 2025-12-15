from __future__ import annotations

import secrets
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status, Form, BackgroundTasks, Response, Body, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.security.utils import get_authorization_scheme_param
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt, JWTError

from app.api.deps import get_db_session
from app.core.config import admin_auth_enabled, settings
from app.core import security
from app.models.user import User, UserRole
from app.services.auth_service import get_current_user as get_auth_user, AuthError


def safe_form_get(form_data: dict[str, Any], key: str, default: str = "") -> str:
    """Safely extract string value from form data (handles UploadFile case)."""
    value = form_data.get(key, default)
    if isinstance(value, UploadFile):
        return default
    return str(value) if value is not None else default
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
from app.crud.lead import list_leads, get_lead_by_id
from app.crud.chat_log import (
    list_chat_logs_for_tenant, 
    get_inbox_conversations, 
    get_chat_history_for_lead, 
    create_chat_log
)
from app.crud.knowledge_base import (
    create_kb_item,
    delete_kb_item,
    list_kb_items,
)
from app.crud.broadcast import (
    create_broadcast,
    list_broadcasts,
    get_broadcast,
    update_broadcast_stats,
)
from app.crud.flow import (
    create_flow,
    list_flows,
    get_flow,
    update_flow,
    delete_flow,
)
from app.models.broadcast import BroadcastStatus
from app.models.chat_log import SenderType
from app.services.telegram_service import send_telegram_message
from app.services.meta_service import send_whatsapp_reply, send_page_message_text
from app.crud.stats import get_dashboard_stats, get_messages_per_day, get_recent_activity
from app.crud.message_template import (
    create_message_template,
    delete_message_template,
    list_message_templates,
    seed_default_templates,
)
from app.services.broadcast_service import execute_broadcast

# Templates directory (app/templates)
TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
jinja_templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

public_router = APIRouter(prefix="/ui", tags=["ui"])

@public_router.get("/welcome", response_class=HTMLResponse)
async def welcome_page(request: Request):
    return jinja_templates.TemplateResponse("landing.html", {"request": request})

@public_router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return jinja_templates.TemplateResponse("login.html", {"request": request})

@public_router.post("/login", response_class=HTMLResponse)
async def login_submit(request: Request, password: str = Form(...)):
    # In a real app, you'd hash the password in config or env var.
    # Here we compare with the configured admin password.
    if password != settings.admin_password:
         return jinja_templates.TemplateResponse("login.html", {"request": request, "error": "Invalid password"})
    
    access_token = security.create_access_token(subject="admin")
    response = RedirectResponse(url="/ui/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(key="access_token", value=access_token, httponly=True)
    return response

@public_router.get("/logout")
async def logout():
    response = RedirectResponse(url="/ui/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return response

async def check_auth(request: Request, session: AsyncSession = Depends(get_db_session)) -> Optional[User]:
    """
    Check authentication - supports both legacy admin password and new user-based auth.
    Returns User object if authenticated via new system, None if via legacy admin.
    """
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=status.HTTP_307_TEMPORARY_REDIRECT, headers={"Location": "/ui/login"})
    
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[security.ALGORITHM])
        
        # Legacy admin auth (sub="admin")
        if payload.get("sub") == "admin":
            return None  # Legacy admin mode
        
        # New user-based auth (sub=user_id)
        user_id = payload.get("sub")
        if user_id:
            try:
                user = await get_auth_user(session, token)
                return user
            except AuthError:
                raise HTTPException(status_code=status.HTTP_307_TEMPORARY_REDIRECT, headers={"Location": "/ui/auth/login"})
        
        raise HTTPException(status_code=status.HTTP_307_TEMPORARY_REDIRECT, headers={"Location": "/ui/login"})
    except JWTError:
        raise HTTPException(status_code=status.HTTP_307_TEMPORARY_REDIRECT, headers={"Location": "/ui/login"})

protected_router = APIRouter(prefix="/ui", tags=["ui"], dependencies=[Depends(check_auth)])


async def _get_ai_models() -> list[str]:
    """Best-effort fetch of available models from the configured OpenAI-compatible endpoint."""

    llm_key = settings.effective_llm_api_key()
    if not llm_key:
        return []

    try:
        async with httpx.AsyncClient(
            base_url=settings.llm_base_url, timeout=10.0
        ) as client:
            resp = await client.get(
                "/models", headers={"Authorization": f"Bearer {llm_key}"}
            )
            resp.raise_for_status()
            data = resp.json() or {}
        models = [
            str(m.get("id"))
            for m in (data.get("data") or [])
            if m and m.get("id")
        ]
        return sorted(set(models))
    except Exception:
        return []


async def _settings_ai_context(request: Request) -> dict:
    ai_configured = bool(settings.effective_llm_api_key())

    llm_url = (settings.llm_base_url or "").lower()
    if "groq" in llm_url:
        ai_provider = "Groq"
    elif "nvidia" in llm_url or "nim" in llm_url:
        ai_provider = "NVIDIA NIM"
    elif "openai" in llm_url:
        ai_provider = "OpenAI"
    else:
        ai_provider = "Custom LLM"

    base_url = str(request.base_url).rstrip("/")
    ai_models = await _get_ai_models() if ai_configured else []

    return {
        "ai_configured": ai_configured,
        "ai_provider": ai_provider,
        "ai_model": settings.effective_llm_model(),
        "ai_models": ai_models,
        "base_url": base_url,
    }


def _require_admin_password(admin_password: str) -> None:
    if not admin_auth_enabled():
        return
    if admin_password != settings.admin_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin_password"
        )


@protected_router.get("/")
async def ui_root(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
):
    """Show onboarding for first-time users, otherwise go to dashboard"""
    tenants = await list_tenants(session=session)
    if not tenants:
        return jinja_templates.TemplateResponse("onboarding.html", {"request": request})
    return RedirectResponse(url="/ui/dashboard", status_code=status.HTTP_302_FOUND)


# ============ DASHBOARD ============
@protected_router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(
    request: Request,
    tenant_id: int | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    """Main dashboard with statistics"""
    tenants = await list_tenants(session=session)
    
    # Get statistics
    stats = await get_dashboard_stats(session=session, tenant_id=tenant_id)
    chart_data = await get_messages_per_day(session=session, tenant_id=tenant_id, days=7)
    recent_activity = await get_recent_activity(session=session, tenant_id=tenant_id, limit=10)
    
    # Calculate max for chart scaling
    max_count = max((d["count"] for d in chart_data), default=1)
    
    return jinja_templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "tenants": tenants,
            "selected_tenant_id": tenant_id,
            "stats": stats,
            "chart_data": chart_data,
            "max_count": max_count,
            "recent_activity": recent_activity,
        },
    )


# ============ TENANTS ============
@protected_router.get("/tenants", response_class=HTMLResponse)
async def tenants_page(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    tenants = await list_tenants(session=session)
    return jinja_templates.TemplateResponse(
        "tenants.html",
        {"request": request, "tenants": tenants, "admin_protected": admin_auth_enabled()},
    )


@protected_router.get("/tenants/rows", response_class=HTMLResponse)
async def tenants_rows(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    tenants = await list_tenants(session=session)
    return jinja_templates.TemplateResponse(
        "_tenant_rows.html",
        {"request": request, "tenants": tenants},
    )


@protected_router.post("/tenants", response_class=HTMLResponse)
async def create_tenant_web(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    form = dict(await request.form())
    name = safe_form_get(form, "name").strip()
    admin_password = safe_form_get(form, "admin_password")
    system_prompt = safe_form_get(form, "system_prompt") or None
    webhook_url = safe_form_get(form, "webhook_url") or None
    
    if not name:
        raise HTTPException(status_code=400, detail="Name is required")
    
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
    return jinja_templates.TemplateResponse(
        "_tenant_rows.html", {"request": request, "tenants": tenants}, status_code=status.HTTP_201_CREATED
    )


@protected_router.post("/tenants/{tenant_id}/rotate", response_class=HTMLResponse)
async def rotate_tenant_key(
    request: Request,
    tenant_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    form = dict(await request.form())
    admin_password = form.get("admin_password", "")
    _require_admin_password(admin_password)
    tenant = await get_tenant_by_id(session=session, tenant_id=tenant_id)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    await rotate_tenant_api_key(session=session, tenant=tenant, new_api_key=secrets.token_urlsafe(32))
    tenants = await list_tenants(session=session)
    return jinja_templates.TemplateResponse(
        "_tenant_rows.html", {"request": request, "tenants": tenants}, status_code=status.HTTP_200_OK
    )


@protected_router.post("/tenants/{tenant_id}/update", response_class=HTMLResponse)
async def update_tenant_web(
    request: Request,
    tenant_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    form = dict(await request.form())
    name = safe_form_get(form, "name", "").strip()
    admin_password = form.get("admin_password", "")
    
    if not name:
        raise HTTPException(status_code=400, detail="Name is required")
    
    _require_admin_password(admin_password)
    tenant = await get_tenant_by_id(session=session, tenant_id=tenant_id)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    await update_tenant_name(session=session, tenant=tenant, name=name)
    tenants = await list_tenants(session=session)
    return jinja_templates.TemplateResponse(
        "_tenant_rows.html", {"request": request, "tenants": tenants}, status_code=status.HTTP_200_OK
    )


@protected_router.post("/tenants/{tenant_id}/delete", response_class=HTMLResponse)
async def delete_tenant_web(
    request: Request,
    tenant_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    form = dict(await request.form())
    admin_password = form.get("admin_password", "")
    _require_admin_password(admin_password)
    tenant = await get_tenant_by_id(session=session, tenant_id=tenant_id)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    await delete_tenant(session=session, tenant=tenant)
    tenants = await list_tenants(session=session)
    return jinja_templates.TemplateResponse(
        "_tenant_rows.html", {"request": request, "tenants": tenants}, status_code=status.HTTP_200_OK
    )


# ============ CHANNELS ============
@protected_router.get("/channels", response_class=HTMLResponse)
async def channels_page(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    tenants = await list_tenants(session=session)
    return jinja_templates.TemplateResponse("channels.html", {"request": request, "tenants": tenants})


@protected_router.get("/channels/rows", response_class=HTMLResponse)
async def channels_rows(
    request: Request,
    tenant_api_key: str = "",
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    if not tenant_api_key:
        return jinja_templates.TemplateResponse(
            "_channel_rows.html", {"request": request, "channels": [], "error": "اختر مشروعاً أولاً"}
        )
    tenant = await get_tenant_by_api_key(session=session, api_key=tenant_api_key)
    if not tenant:
        return jinja_templates.TemplateResponse(
            "_channel_rows.html", {"request": request, "channels": [], "error": "مفتاح API غير صالح"}
        )
    channels = await list_integrations_for_tenant(session=session, tenant_id=tenant.id)
    base_url = str(request.base_url).rstrip('/')
    return jinja_templates.TemplateResponse(
        "_channel_rows.html",
        {"request": request, "channels": channels, "tenant": tenant, "base_url": base_url},
    )


@protected_router.post("/channels", response_class=HTMLResponse)
async def create_channel_web(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    form = dict(await request.form())
    tenant_api_key = safe_form_get(form, "tenant_api_key").strip()
    channel_type = safe_form_get(form, "channel_type").strip().lower()
    external_id = safe_form_get(form, "external_id").strip()
    access_token = safe_form_get(form, "access_token").strip()
    verify_token = safe_form_get(form, "verify_token").strip() or secrets.token_urlsafe(16)
    is_active = safe_form_get(form, "is_active", "true").lower() == "true"
    
    if not tenant_api_key:
        return jinja_templates.TemplateResponse(
            "_channel_rows.html", {"request": request, "channels": [], "error": "مفتاح API مطلوب"}
        )
    
    tenant = await get_tenant_by_api_key(session=session, api_key=tenant_api_key)
    if not tenant:
        return jinja_templates.TemplateResponse(
            "_channel_rows.html", {"request": request, "channels": [], "error": "مفتاح API غير صالح"}
        )
    
    await create_integration(
        session=session,
        tenant_id=tenant.id,
        channel_type=channel_type,
        external_id=external_id or None,
        access_token=access_token or None,
        verify_token=verify_token,
        is_active=is_active,
    )
    channels = await list_integrations_for_tenant(session=session, tenant_id=tenant.id)
    base_url = str(request.base_url).rstrip('/')
    return jinja_templates.TemplateResponse(
        "_channel_rows.html",
        {"request": request, "channels": channels, "tenant": tenant, "base_url": base_url},
        status_code=status.HTTP_201_CREATED,
    )


@protected_router.post("/channels/{channel_id}/delete", response_class=HTMLResponse)
async def delete_channel_web(
    request: Request,
    channel_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    form = dict(await request.form())
    tenant_api_key = safe_form_get(form, "tenant_api_key", "").strip()
    
    tenant = await get_tenant_by_api_key(session=session, api_key=tenant_api_key)
    if not tenant:
        return jinja_templates.TemplateResponse(
            "_channel_rows.html", {"request": request, "channels": [], "error": "مفتاح API غير صالح"}
        )
    
    channel = await get_integration_by_id(session=session, integration_id=channel_id)
    if channel and channel.tenant_id == tenant.id:
        await delete_integration(session=session, integration=channel)
    
    channels = await list_integrations_for_tenant(session=session, tenant_id=tenant.id)
    base_url = str(request.base_url).rstrip('/')
    return jinja_templates.TemplateResponse(
        "_channel_rows.html",
        {"request": request, "channels": channels, "tenant": tenant, "base_url": base_url},
    )


# ============ QUICK REPLIES ============
@protected_router.get("/quick-replies", response_class=HTMLResponse)
async def quick_replies_page(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    tenants = await list_tenants(session=session)
    return jinja_templates.TemplateResponse("quick_replies.html", {"request": request, "tenants": tenants})


@protected_router.get("/quick-replies/rows", response_class=HTMLResponse)
async def quick_replies_rows(
    request: Request,
    tenant_api_key: str = "",
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    if not tenant_api_key:
        return jinja_templates.TemplateResponse(
            "_quick_reply_rows.html", {"request": request, "replies": [], "error": "اختر مشروعاً أولاً"}
        )
    tenant = await get_tenant_by_api_key(session=session, api_key=tenant_api_key)
    if not tenant:
        return jinja_templates.TemplateResponse(
            "_quick_reply_rows.html", {"request": request, "replies": [], "error": "مفتاح API غير صالح"}
        )
    replies = await list_quick_replies_for_tenant(session=session, tenant_id=tenant.id)
    return jinja_templates.TemplateResponse("_quick_reply_rows.html", {"request": request, "replies": replies, "tenant": tenant})


@protected_router.post("/quick-replies", response_class=HTMLResponse)
async def create_quick_reply_web(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    form = dict(await request.form())
    tenant_api_key = safe_form_get(form, "tenant_api_key", "").strip()
    title = safe_form_get(form, "title", "").strip()
    payload_text = safe_form_get(form, "payload_text", "").strip()
    sort_order = int(form.get("sort_order", "0") or "0")
    is_active = safe_form_get(form, "is_active", "true").lower() == "true"
    
    if not tenant_api_key:
        return jinja_templates.TemplateResponse(
            "_quick_reply_rows.html", {"request": request, "replies": [], "error": "مفتاح API مطلوب"}
        )
    
    tenant = await get_tenant_by_api_key(session=session, api_key=tenant_api_key)
    if not tenant:
        return jinja_templates.TemplateResponse(
            "_quick_reply_rows.html", {"request": request, "replies": [], "error": "مفتاح API غير صالح"}
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
    return jinja_templates.TemplateResponse(
        "_quick_reply_rows.html", {"request": request, "replies": replies, "tenant": tenant}, status_code=status.HTTP_201_CREATED
    )


@protected_router.post("/quick-replies/{reply_id}/delete", response_class=HTMLResponse)
async def delete_quick_reply_web(
    request: Request,
    reply_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    form = dict(await request.form())
    tenant_api_key = safe_form_get(form, "tenant_api_key", "").strip()
    
    tenant = await get_tenant_by_api_key(session=session, api_key=tenant_api_key)
    if not tenant:
        return jinja_templates.TemplateResponse(
            "_quick_reply_rows.html", {"request": request, "replies": [], "error": "مفتاح API غير صالح"}
        )
    
    reply = await get_quick_reply_by_id(session=session, quick_reply_id=reply_id)
    if reply and reply.tenant_id == tenant.id:
        await delete_quick_reply(session=session, quick_reply=reply)
    
    replies = await list_quick_replies_for_tenant(session=session, tenant_id=tenant.id)
    return jinja_templates.TemplateResponse("_quick_reply_rows.html", {"request": request, "replies": replies, "tenant": tenant})


# ============ RULES (Scripted Responses) ============
@protected_router.get("/rules", response_class=HTMLResponse)
async def rules_page(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    tenants = await list_tenants(session=session)
    return jinja_templates.TemplateResponse("rules.html", {"request": request, "tenants": tenants})


@protected_router.get("/rules/rows", response_class=HTMLResponse)
async def rules_rows(
    request: Request,
    tenant_api_key: str = "",
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    if not tenant_api_key:
        return jinja_templates.TemplateResponse(
            "_rule_rows.html", {"request": request, "rules": [], "error": "اختر مشروعاً أولاً"}
        )
    tenant = await get_tenant_by_api_key(session=session, api_key=tenant_api_key)
    if not tenant:
        return jinja_templates.TemplateResponse(
            "_rule_rows.html", {"request": request, "rules": [], "error": "مفتاح API غير صالح"}
        )
    rules = await list_active_scripted_responses(session=session, tenant_id=tenant.id)
    return jinja_templates.TemplateResponse("_rule_rows.html", {"request": request, "rules": rules, "tenant": tenant})


@protected_router.post("/rules", response_class=HTMLResponse)
async def create_rule_web(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    form = dict(await request.form())
    tenant_api_key = safe_form_get(form, "tenant_api_key", "").strip()
    trigger_keyword = safe_form_get(form, "trigger_keyword", "").strip()
    response_text = safe_form_get(form, "response_text", "").strip()
    is_active = safe_form_get(form, "is_active", "true").lower() == "true"
    
    if not tenant_api_key:
        return jinja_templates.TemplateResponse(
            "_rule_rows.html", {"request": request, "rules": [], "error": "مفتاح API مطلوب"}
        )
    
    tenant = await get_tenant_by_api_key(session=session, api_key=tenant_api_key)
    if not tenant:
        return jinja_templates.TemplateResponse(
            "_rule_rows.html", {"request": request, "rules": [], "error": "مفتاح API غير صالح"}
        )
    
    await create_scripted_response(
        session=session,
        tenant_id=tenant.id,
        trigger_keyword=trigger_keyword,
        response_text=response_text,
        is_active=is_active,
    )
    rules = await list_active_scripted_responses(session=session, tenant_id=tenant.id)
    return jinja_templates.TemplateResponse(
        "_rule_rows.html", {"request": request, "rules": rules, "tenant": tenant}, status_code=status.HTTP_201_CREATED
    )


@protected_router.post("/rules/{rule_id}/delete", response_class=HTMLResponse)
async def delete_rule_web(
    request: Request,
    rule_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    form = dict(await request.form())
    tenant_api_key = safe_form_get(form, "tenant_api_key", "").strip()
    
    tenant = await get_tenant_by_api_key(session=session, api_key=tenant_api_key)
    if not tenant:
        return jinja_templates.TemplateResponse(
            "_rule_rows.html", {"request": request, "rules": [], "error": "مفتاح API غير صالح"}
        )
    
    rule = await get_scripted_response_by_id(session=session, scripted_response_id=rule_id)
    if rule and rule.tenant_id == tenant.id:
        await delete_scripted_response(session=session, scripted_response=rule)
    
    rules = await list_active_scripted_responses(session=session, tenant_id=tenant.id)
    return jinja_templates.TemplateResponse("_rule_rows.html", {"request": request, "rules": rules, "tenant": tenant})


# ============ LEADS ============
@protected_router.get("/leads", response_class=HTMLResponse)
async def leads_page(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    tenants = await list_tenants(session=session)
    return jinja_templates.TemplateResponse("leads.html", {"request": request, "tenants": tenants})


@protected_router.get("/leads/rows", response_class=HTMLResponse)
async def leads_rows(
    request: Request,
    tenant_api_key: str = "",
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    if not tenant_api_key:
        return jinja_templates.TemplateResponse(
            "_lead_rows.html", {"request": request, "leads": [], "error": "اختر مشروعاً أولاً"}
        )
    tenant = await get_tenant_by_api_key(session=session, api_key=tenant_api_key)
    if not tenant:
        return jinja_templates.TemplateResponse(
            "_lead_rows.html", {"request": request, "leads": [], "error": "مفتاح API غير صالح"}
        )
    leads = await list_leads(session=session, tenant_id=tenant.id)
    return jinja_templates.TemplateResponse("_lead_rows.html", {"request": request, "leads": leads, "tenant": tenant})


# ============ CHAT LOGS ============
@protected_router.get("/chatlogs", response_class=HTMLResponse)
async def chatlogs_page(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    tenants = await list_tenants(session=session)
    return jinja_templates.TemplateResponse("chatlogs.html", {"request": request, "tenants": tenants})


@protected_router.get("/chatlogs/rows", response_class=HTMLResponse)
async def chatlogs_rows(
    request: Request,
    tenant_api_key: str = "",
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    if not tenant_api_key:
        return jinja_templates.TemplateResponse(
            "_chatlog_rows.html", {"request": request, "logs": [], "error": "اختر مشروعاً أولاً"}
        )
    tenant = await get_tenant_by_api_key(session=session, api_key=tenant_api_key)
    if not tenant:
        return jinja_templates.TemplateResponse(
            "_chatlog_rows.html", {"request": request, "logs": [], "error": "مفتاح API غير صالح"}
        )
    logs = await list_chat_logs_for_tenant(session=session, tenant_id=tenant.id, limit=200)
    return jinja_templates.TemplateResponse("_chatlog_rows.html", {"request": request, "logs": logs, "tenant": tenant})


# ============ SETTINGS ============
@protected_router.get("/settings", response_class=HTMLResponse)
async def settings_page(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    tenants = await list_tenants(session=session)
    base_url = str(request.base_url).rstrip('/')
    return jinja_templates.TemplateResponse("settings.html", {"request": request, "tenants": tenants, "base_url": base_url})


@protected_router.get("/settings/full", response_class=HTMLResponse)
async def settings_full(
    request: Request,
    tenant_api_key: str = "",
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    """Full settings view with AI status and webhooks"""
    if not tenant_api_key:
        return jinja_templates.TemplateResponse(
            "_settings_form.html",
            {"request": request, "tenant": None},
        )
    
    tenant = await get_tenant_by_api_key(session=session, api_key=tenant_api_key)
    if not tenant:
        return jinja_templates.TemplateResponse(
            "_settings_form.html",
            {"request": request, "tenant": None},
        )

    integrations = await list_integrations_for_tenant(
        session=session, tenant_id=tenant.id
    )
    
    ai_ctx = await _settings_ai_context(request)

    return jinja_templates.TemplateResponse(
        "_settings_form.html",
        {
            "request": request,
            "tenant": tenant,
            "integrations": integrations,
            **ai_ctx,
        },
    )


@protected_router.get("/settings/data", response_class=HTMLResponse)
async def settings_data(
    request: Request,
    tenant_api_key: str = "",
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    if not tenant_api_key:
        return jinja_templates.TemplateResponse(
            "_settings_form.html",
            {"request": request, "tenant": None, "error": "اختر مشروعاً أولاً"},
        )
    tenant = await get_tenant_by_api_key(session=session, api_key=tenant_api_key)
    if not tenant:
        return jinja_templates.TemplateResponse(
            "_settings_form.html",
            {"request": request, "tenant": None, "error": "مفتاح API غير صالح"},
        )

    integrations = await list_integrations_for_tenant(
        session=session, tenant_id=tenant.id
    )
    
    ai_ctx = await _settings_ai_context(request)

    return jinja_templates.TemplateResponse(
        "_settings_form.html", 
        {
            "request": request, 
            "tenant": tenant,
            "integrations": integrations,
            **ai_ctx,
        }
    )


@protected_router.post("/settings/update", response_class=HTMLResponse)
async def update_settings_web(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    form = dict(await request.form())
    tenant_api_key = safe_form_get(form, "tenant_api_key", "").strip()
    system_prompt = safe_form_get(form, "system_prompt", "").strip()
    webhook_url = safe_form_get(form, "webhook_url", "").strip()
    
    if not tenant_api_key:
        return jinja_templates.TemplateResponse(
            "_settings_form.html",
            {"request": request, "tenant": None, "error": "مفتاح API مطلوب"},
        )
    
    tenant = await get_tenant_by_api_key(session=session, api_key=tenant_api_key)
    if not tenant:
        return jinja_templates.TemplateResponse(
            "_settings_form.html",
            {"request": request, "tenant": None, "error": "مفتاح API غير صالح"},
        )
    
    await update_tenant_settings(
        session=session,
        tenant=tenant,
        system_prompt=system_prompt or None,
        webhook_url=webhook_url or None,
    )
    refreshed = await get_tenant_by_id(session=session, tenant_id=tenant.id)
    if refreshed is not None:
        tenant = refreshed

    integrations = await list_integrations_for_tenant(
        session=session, tenant_id=tenant.id
    )

    ai_ctx = await _settings_ai_context(request)
    return jinja_templates.TemplateResponse(
        "_settings_form.html",
        {
            "request": request,
            "tenant": tenant,
            "integrations": integrations,
            "success": "تم حفظ الإعدادات بنجاح ✓",
            **ai_ctx,
        },
    )


# ============ TEST CHAT ============
@protected_router.get("/test-chat", response_class=HTMLResponse)
async def test_chat_page(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    tenants = await list_tenants(session=session)
    return jinja_templates.TemplateResponse("test_chat.html", {"request": request, "tenants": tenants})


@protected_router.post("/test-chat/send", response_class=HTMLResponse)
async def send_test_message(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    """Process test chat message and return AI response"""
    form = dict(await request.form())
    tenant_api_key = safe_form_get(form, "tenant_api_key", "").strip()
    message = safe_form_get(form, "message", "").strip()
    
    if not tenant_api_key or not message:
        return HTMLResponse(
            '<div class="text-red-400 text-sm">الرجاء اختيار مشروع وكتابة رسالة</div>'
        )
    
    tenant = await get_tenant_by_api_key(session=session, api_key=tenant_api_key)
    if not tenant:
        return HTMLResponse(
            '<div class="text-red-400 text-sm">مفتاح API غير صالح</div>'
        )
    
    try:
        from app.services.chat_service import ChatManager

        manager = ChatManager(session=session)
        result = await manager.process_message(tenant_id=tenant.id, user_message=message)
        
        return jinja_templates.TemplateResponse(
            "_chat_message.html",
            {
                "request": request,
                "user_message": message,
                "bot_response": result.response,
                "timestamp": datetime.now().strftime("%H:%M"),
            }
        )
    except Exception as e:
        return HTMLResponse(
            f'<div class="text-red-400 text-sm">خطأ: {str(e)}</div>'
        )


# ============ WIDGET GENERATOR ============
@protected_router.get("/widget", response_class=HTMLResponse)
async def widget_page(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    tenants = await list_tenants(session=session)
    return jinja_templates.TemplateResponse("widget.html", {"request": request, "tenants": tenants})


@protected_router.get("/widget/generate", response_class=HTMLResponse)
async def generate_widget_code(
    request: Request,
    tenant_api_key: str = "",
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    if not tenant_api_key:
        return HTMLResponse('<div class="text-red-400">اختر مشروعاً أولاً</div>')
    
    tenant = await get_tenant_by_api_key(session=session, api_key=tenant_api_key)
    if not tenant:
        return HTMLResponse('<div class="text-red-400">مفتاح API غير صالح</div>')
    
    # Get base URL from request
    base_url = str(request.base_url).rstrip('/')
    
    return jinja_templates.TemplateResponse(
        "_widget_code.html",
        {"request": request, "tenant": tenant, "api_key": tenant_api_key, "base_url": base_url}
    )


# ============ WIDGET EMBED ENDPOINT ============
@protected_router.get("/embed/{api_key}", response_class=HTMLResponse)
async def widget_embed(
    request: Request,
    api_key: str,
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    """Embeddable chat widget for external websites"""
    tenant = await get_tenant_by_api_key(session=session, api_key=api_key)
    if not tenant:
        return HTMLResponse('<div style="color:red;">Invalid API Key</div>')
    
    base_url = str(request.base_url).rstrip('/')
    
    return jinja_templates.TemplateResponse(
        "embed_widget.html",
        {"request": request, "tenant": tenant, "api_key": api_key, "base_url": base_url}
    )


@protected_router.post("/embed/chat", response_class=HTMLResponse)
async def widget_chat(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    """Handle widget chat messages"""
    form = dict(await request.form())
    api_key = safe_form_get(form, "api_key", "").strip()
    message = safe_form_get(form, "message", "").strip()
    session_id = safe_form_get(form, "session_id", "").strip()
    
    tenant = await get_tenant_by_api_key(session=session, api_key=api_key)
    if not tenant:
        return HTMLResponse('<div class="widget-error">Invalid configuration</div>')
    
    try:
        from app.services.chat_service import ChatManager

        manager = ChatManager(session=session)
        result = await manager.process_message(tenant_id=tenant.id, user_message=message)
        return HTMLResponse(f'<div class="bot-message">{result.response}</div>')
    except Exception as e:
        return HTMLResponse(f'<div class="widget-error">Error: {str(e)}</div>')


# ============ MESSAGE TEMPLATES ============
@protected_router.get("/templates", response_class=HTMLResponse)
async def templates_page(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    """Message templates management page"""
    tenants = await list_tenants(session=session)
    return jinja_templates.TemplateResponse(
        "templates.html",
        {"request": request, "tenants": tenants},
    )


@protected_router.get("/templates/list", response_class=HTMLResponse)
async def templates_list(
    request: Request,
    tenant_id: int,
    category: str | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    """List templates for a tenant"""
    msg_templates = await list_message_templates(
        session=session,
        tenant_id=tenant_id,
        category=category,
    )
    return jinja_templates.TemplateResponse(
        "_template_rows.html",
        {"request": request, "templates": msg_templates},
    )


@protected_router.post("/templates/add", response_class=HTMLResponse)
async def templates_add(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    """Add a new message template"""
    form = dict(await request.form())
    tenant_id = int(safe_form_get(form, "tenant_id", 0))
    name = safe_form_get(form, "name", "").strip()
    category = safe_form_get(form, "category", "general").strip()
    content = safe_form_get(form, "content", "").strip()
    variables = safe_form_get(form, "variables", "").strip() or None
    
    if tenant_id and name and content:
        await create_message_template(
            session=session,
            tenant_id=tenant_id,
            name=name,
            category=category,
            content=content,
            variables=variables,
        )
    
    msg_templates = await list_message_templates(session=session, tenant_id=tenant_id)
    return jinja_templates.TemplateResponse(
        "_template_rows.html",
        {"request": request, "templates": msg_templates},
    )


@protected_router.post("/templates/delete", response_class=HTMLResponse)
async def templates_delete(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    """Delete a message template"""
    form = dict(await request.form())
    template_id = int(safe_form_get(form, "template_id", 0))
    tenant_id = int(safe_form_get(form, "tenant_id", 0))
    
    if template_id:
        await delete_message_template(session=session, template_id=template_id)
    
    msg_templates = await list_message_templates(session=session, tenant_id=tenant_id)
    return jinja_templates.TemplateResponse(
        "_template_rows.html",
        {"request": request, "templates": msg_templates},
    )


@protected_router.post("/templates/seed", response_class=HTMLResponse)
async def templates_seed(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    """Seed default templates for a tenant"""
    form = dict(await request.form())
    tenant_id = int(safe_form_get(form, "tenant_id", 0))
    
    if tenant_id:
        await seed_default_templates(session=session, tenant_id=tenant_id)
    
    msg_templates = await list_message_templates(session=session, tenant_id=tenant_id)
    return jinja_templates.TemplateResponse(
        "_template_rows.html",
        {"request": request, "templates": msg_templates},
    )


# ------------------------------------------------------------------------------
# Inbox Routes
# ------------------------------------------------------------------------------

@protected_router.get("/inbox", response_class=HTMLResponse)
async def inbox_page(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
):
    tenants = await list_tenants(session=session)
    return jinja_templates.TemplateResponse(
        "inbox.html",
        {"request": request, "tenants": tenants, "base_url": str(request.base_url).rstrip('/')},
    )

@protected_router.get("/inbox/conversations", response_class=HTMLResponse)
async def inbox_conversations(
    request: Request,
    tenant_api_key: str,
    session: AsyncSession = Depends(get_db_session),
):
    tenant = await get_tenant_by_api_key(session=session, api_key=tenant_api_key)
    if not tenant:
        return HTMLResponse("Tenant not found", status_code=404)
    
    conversations = await get_inbox_conversations(session=session, tenant_id=tenant.id)
    return jinja_templates.TemplateResponse(
        "_inbox_conversations.html",
        {"request": request, "conversations": conversations},
    )

@protected_router.get("/inbox/messages/{lead_id}", response_class=HTMLResponse)
async def inbox_messages(
    request: Request,
    lead_id: int,
    tenant_api_key: str,
    session: AsyncSession = Depends(get_db_session),
):
    # Verify tenant access
    tenant = await get_tenant_by_api_key(session=session, api_key=tenant_api_key)
    if not tenant:
        return HTMLResponse("Tenant not found", status_code=404)
        
    messages = await get_chat_history_for_lead(session=session, lead_id=lead_id)
    return jinja_templates.TemplateResponse(
        "_inbox_messages.html",
        {"request": request, "messages": messages},
    )

@protected_router.post("/inbox/send", response_class=HTMLResponse)
async def inbox_send(
    request: Request,
    tenant_api_key: str = Form(...),
    lead_id: int = Form(...),
    message: str = Form(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    session: AsyncSession = Depends(get_db_session),
):
    tenant = await get_tenant_by_api_key(session=session, api_key=tenant_api_key)
    if not tenant:
        return HTMLResponse("Tenant not found", status_code=404)
        
    lead = await get_lead_by_id(session=session, lead_id=lead_id)
    if not lead:
        return HTMLResponse("Lead not found", status_code=404)

    # 1. Save to DB
    chat_log = await create_chat_log(
        session=session,
        lead_id=lead_id,
        message=message,
        sender_type=SenderType.bot,
    )
    
    # 2. Send to Channel (Heuristic)
    integrations = await list_integrations_for_tenant(session=session, tenant_id=tenant.id)
    
    phone = lead.phone_number or ""
    
    if phone.isdigit() and len(phone) < 16: # Likely Telegram
        target_integ = next((i for i in integrations if i.channel_type == 'telegram'), None)
        if target_integ:
            background_tasks.add_task(
                send_telegram_message,
                bot_token=target_integ.access_token,
                chat_id=int(phone),
                text=message
            )
            
    elif any(i.channel_type == 'whatsapp' for i in integrations): # WhatsApp
         target_integ = next((i for i in integrations if i.channel_type == 'whatsapp'), None)
         if target_integ:
             background_tasks.add_task(
                 send_whatsapp_reply,
                 access_token=target_integ.access_token,
                 phone_number_id=target_integ.external_id,
                 to=phone,
                 text=message
             )
             
    # ... handle others
    
    # Return the new message rendered
    return jinja_templates.TemplateResponse(
        "_inbox_messages.html",
        {"request": request, "messages": [chat_log]},
    )


# ------------------------------------------------------------------------------
# Knowledge Base Routes
# ------------------------------------------------------------------------------

@protected_router.get("/kb", response_class=HTMLResponse)
async def kb_page(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
):
    tenants = await list_tenants(session=session)
    return jinja_templates.TemplateResponse(
        "knowledge_base.html",
        {"request": request, "tenants": tenants},
    )


@protected_router.get("/kb/list", response_class=HTMLResponse)
async def kb_list(
    request: Request,
    tenant_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    items = await list_kb_items(session=session, tenant_id=tenant_id)
    return jinja_templates.TemplateResponse(
        "_kb_rows.html",
        {"request": request, "items": items},
    )


@protected_router.post("/kb/add", response_class=HTMLResponse)
async def kb_add(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    form = dict(await request.form())
    tenant_id = int(safe_form_get(form, "tenant_id", 0))
    title = safe_form_get(form, "title", "").strip()
    content = safe_form_get(form, "content", "").strip()
    
    if tenant_id and title and content:
        await create_kb_item(
            session=session,
            tenant_id=tenant_id,
            title=title,
            content=content,
        )
    
    items = await list_kb_items(session=session, tenant_id=tenant_id)
    return jinja_templates.TemplateResponse(
        "_kb_rows.html",
        {"request": request, "items": items},
    )


@protected_router.post("/kb/delete", response_class=HTMLResponse)
async def kb_delete(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    form = dict(await request.form())
    item_id = int(safe_form_get(form, "item_id", 0))
    tenant_id = int(safe_form_get(form, "tenant_id", 0))
    
    if item_id:
        await delete_kb_item(session=session, kb_id=item_id)
    
    items = await list_kb_items(session=session, tenant_id=tenant_id)
    return jinja_templates.TemplateResponse(
        "_kb_rows.html",
        {"request": request, "items": items},
    )


# ------------------------------------------------------------------------------
# Broadcast Routes
# ------------------------------------------------------------------------------

@protected_router.get("/broadcasts", response_class=HTMLResponse)
async def broadcasts_page(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
):
    tenants = await list_tenants(session=session)
    return jinja_templates.TemplateResponse(
        "broadcasts.html",
        {"request": request, "tenants": tenants},
    )


@protected_router.get("/broadcasts/list", response_class=HTMLResponse)
async def broadcasts_list(
    request: Request,
    tenant_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    broadcasts = await list_broadcasts(session=session, tenant_id=tenant_id)
    return jinja_templates.TemplateResponse(
        "_broadcast_rows.html",
        {"request": request, "broadcasts": broadcasts},
    )


@protected_router.post("/broadcasts/create", response_class=HTMLResponse)
async def broadcasts_create(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    form = dict(await request.form())
    tenant_id = int(safe_form_get(form, "tenant_id", 0))
    name = safe_form_get(form, "name", "").strip()
    message = safe_form_get(form, "message", "").strip()
    target_channel = safe_form_get(form, "target_channel", "all").strip()
    
    if tenant_id and name and message:
        await create_broadcast(
            session=session,
            tenant_id=tenant_id,
            name=name,
            message=message,
            target_channel=target_channel,
        )
    
    broadcasts = await list_broadcasts(session=session, tenant_id=tenant_id)
    return jinja_templates.TemplateResponse(
        "_broadcast_rows.html",
        {"request": request, "broadcasts": broadcasts},
    )


async def _execute_broadcast_task(broadcast_id: int, tenant_id: int):
    """Background task to send broadcast messages"""
    from app.db.session import async_session_maker
    
    async with async_session_maker() as session:
        broadcast = await get_broadcast(session, broadcast_id)
        if not broadcast:
            return
            
        # Update status to sending
        await update_broadcast_stats(session, broadcast_id, status=BroadcastStatus.sending)
        
        # Fetch leads and integrations
        leads = await list_leads(session=session, tenant_id=tenant_id, limit=1000) # Limit for safety
        integrations = await list_integrations_for_tenant(session=session, tenant_id=tenant_id)
        
        telegram_integ = next((i for i in integrations if i.channel_type == 'telegram'), None)
        whatsapp_integ = next((i for i in integrations if i.channel_type == 'whatsapp'), None)
        
        sent_count = 0
        failed_count = 0
        
        for lead in leads:
            phone = lead.phone_number or ""
            if not phone:
                continue
                
            try:
                # Telegram Logic
                if (broadcast.target_channel in ['all', 'telegram']) and telegram_integ and phone.isdigit() and len(phone) < 16:
                    await send_telegram_message(
                        bot_token=telegram_integ.access_token,
                        chat_id=int(phone),
                        text=broadcast.message
                    )
                    sent_count += 1
                    
                # WhatsApp Logic
                elif (broadcast.target_channel in ['all', 'whatsapp']) and whatsapp_integ:
                    await send_whatsapp_reply(
                        access_token=whatsapp_integ.access_token,
                        phone_number_id=whatsapp_integ.external_id,
                        to=phone,
                        text=broadcast.message
                    )
                    sent_count += 1
                    
            except Exception:
                failed_count += 1
                
        # Update final stats
        await update_broadcast_stats(
            session, 
            broadcast_id, 
            sent=sent_count, 
            failed=failed_count, 
            status=BroadcastStatus.completed
        )


@protected_router.post("/broadcasts/send", response_class=HTMLResponse)
async def broadcasts_send(
    request: Request,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    form = dict(await request.form())
    broadcast_id = int(safe_form_get(form, "broadcast_id", "0"))
    tenant_id = int(safe_form_get(form, "tenant_id", "0"))
    
    if broadcast_id and tenant_id:
        # Use the new broadcast service
        background_tasks.add_task(execute_broadcast, session, broadcast_id)
    
    # Return list immediately (status will update on refresh)
    broadcasts = await list_broadcasts(session=session, tenant_id=tenant_id)
    return jinja_templates.TemplateResponse(
        "_broadcast_rows.html",
        {"request": request, "broadcasts": broadcasts},
    )


# ------------------------------------------------------------------------------
# Flows
# ------------------------------------------------------------------------------

@protected_router.get("/flows", response_class=HTMLResponse)
async def flows_page(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    # For MVP, pick first tenant
    tenants = await list_tenants(session=session)
    if not tenants:
        return RedirectResponse(url="/ui/tenants", status_code=status.HTTP_303_SEE_OTHER)
    tenant_id = tenants[0].id
    
    flows = await list_flows(session=session, tenant_id=tenant_id)
    return jinja_templates.TemplateResponse(
        "flows.html",
        {"request": request, "flows": flows, "tenant_id": tenant_id},
    )


@protected_router.post("/flows", response_class=HTMLResponse)
async def flows_create(
    request: Request,
    name: str = Form(...),
    trigger_keyword: str = Form(None),
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    tenants = await list_tenants(session=session)
    if not tenants:
        return HTMLResponse("No tenant found", status_code=400)
    tenant_id = tenants[0].id
    
    await create_flow(
        session=session,
        tenant_id=tenant_id,
        name=name,
        trigger_keyword=trigger_keyword,
        flow_data={"nodes": []}
    )
    
    flows = await list_flows(session=session, tenant_id=tenant_id)
    return jinja_templates.TemplateResponse(
        "_flow_rows.html",
        {"request": request, "flows": flows},
    )


@protected_router.get("/flows/{flow_id}/builder", response_class=HTMLResponse)
async def flows_builder(
    request: Request,
    flow_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    flow = await get_flow(session, flow_id)
    if not flow:
        raise HTTPException(status_code=404, detail="Flow not found")
    
    # Pass flow_data as JSON string for JS
    flow_json = json.dumps(flow.flow_data.get("nodes", []))
    
    return jinja_templates.TemplateResponse(
        "flow_builder.html",
        {"request": request, "flow": flow, "flow_json": flow_json},
    )


@protected_router.post("/flows/{flow_id}/update")
async def flows_update(
    flow_id: int,
    flow_data: dict = Body(...),
    session: AsyncSession = Depends(get_db_session),
):
    await update_flow(session, flow_id, flow_data=flow_data)
    return {"status": "ok"}


@protected_router.post("/flows/{flow_id}/delete", response_class=HTMLResponse)
async def flows_delete(
    request: Request,
    flow_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    flow = await get_flow(session, flow_id)
    if flow:
        tenant_id = flow.tenant_id
        await delete_flow(session, flow_id)
        flows = await list_flows(session=session, tenant_id=tenant_id)
        return jinja_templates.TemplateResponse(
            "_flow_rows.html",
            {"request": request, "flows": flows},
        )
    return HTMLResponse("", status_code=200)


# Combine routers
router = APIRouter()
router.include_router(public_router)
router.include_router(protected_router)




