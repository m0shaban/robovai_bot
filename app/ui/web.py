from __future__ import annotations

import secrets
import json
from pathlib import Path
from datetime import datetime

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


@router.get("/")
async def ui_root(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
):
    """Show onboarding for first-time users, otherwise go to tenants page"""
    tenants = await list_tenants(session=session)
    if not tenants:
        return templates.TemplateResponse("onboarding.html", {"request": request})
    return RedirectResponse(url="/ui/tenants", status_code=status.HTTP_302_FOUND)


# ============ TENANTS ============
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
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    form = await request.form()
    name = form.get("name", "").strip()
    admin_password = form.get("admin_password", "")
    system_prompt = form.get("system_prompt") or None
    webhook_url = form.get("webhook_url") or None
    
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
    return templates.TemplateResponse(
        "_tenant_rows.html", {"request": request, "tenants": tenants}, status_code=status.HTTP_201_CREATED
    )


@router.post("/tenants/{tenant_id}/rotate", response_class=HTMLResponse)
async def rotate_tenant_key(
    request: Request,
    tenant_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    form = await request.form()
    admin_password = form.get("admin_password", "")
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
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    form = await request.form()
    name = form.get("name", "").strip()
    admin_password = form.get("admin_password", "")
    
    if not name:
        raise HTTPException(status_code=400, detail="Name is required")
    
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
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    form = await request.form()
    admin_password = form.get("admin_password", "")
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
async def channels_page(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    tenants = await list_tenants(session=session)
    return templates.TemplateResponse("channels.html", {"request": request, "tenants": tenants})


@router.get("/channels/rows", response_class=HTMLResponse)
async def channels_rows(
    request: Request,
    tenant_api_key: str = "",
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    if not tenant_api_key:
        return templates.TemplateResponse(
            "_channel_rows.html", {"request": request, "channels": [], "error": "اختر مشروعاً أولاً"}
        )
    tenant = await get_tenant_by_api_key(session=session, api_key=tenant_api_key)
    if not tenant:
        return templates.TemplateResponse(
            "_channel_rows.html", {"request": request, "channels": [], "error": "مفتاح API غير صالح"}
        )
    channels = await list_integrations_for_tenant(session=session, tenant_id=tenant.id)
    return templates.TemplateResponse("_channel_rows.html", {"request": request, "channels": channels, "tenant": tenant})


@router.post("/channels", response_class=HTMLResponse)
async def create_channel_web(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    form = await request.form()
    tenant_api_key = form.get("tenant_api_key", "").strip()
    channel_type = form.get("channel_type", "").strip().lower()
    external_id = form.get("external_id", "").strip()
    access_token = form.get("access_token", "").strip()
    verify_token = form.get("verify_token", "").strip() or secrets.token_urlsafe(16)
    is_active = form.get("is_active", "true").lower() == "true"
    
    if not tenant_api_key:
        return templates.TemplateResponse(
            "_channel_rows.html", {"request": request, "channels": [], "error": "مفتاح API مطلوب"}
        )
    
    tenant = await get_tenant_by_api_key(session=session, api_key=tenant_api_key)
    if not tenant:
        return templates.TemplateResponse(
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
    return templates.TemplateResponse(
        "_channel_rows.html", {"request": request, "channels": channels, "tenant": tenant}, status_code=status.HTTP_201_CREATED
    )


@router.post("/channels/{channel_id}/delete", response_class=HTMLResponse)
async def delete_channel_web(
    request: Request,
    channel_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    form = await request.form()
    tenant_api_key = form.get("tenant_api_key", "").strip()
    
    tenant = await get_tenant_by_api_key(session=session, api_key=tenant_api_key)
    if not tenant:
        return templates.TemplateResponse(
            "_channel_rows.html", {"request": request, "channels": [], "error": "مفتاح API غير صالح"}
        )
    
    channel = await get_integration_by_id(session=session, integration_id=channel_id)
    if channel and channel.tenant_id == tenant.id:
        await delete_integration(session=session, integration=channel)
    
    channels = await list_integrations_for_tenant(session=session, tenant_id=tenant.id)
    return templates.TemplateResponse("_channel_rows.html", {"request": request, "channels": channels, "tenant": tenant})


# ============ QUICK REPLIES ============
@router.get("/quick-replies", response_class=HTMLResponse)
async def quick_replies_page(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    tenants = await list_tenants(session=session)
    return templates.TemplateResponse("quick_replies.html", {"request": request, "tenants": tenants})


@router.get("/quick-replies/rows", response_class=HTMLResponse)
async def quick_replies_rows(
    request: Request,
    tenant_api_key: str = "",
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    if not tenant_api_key:
        return templates.TemplateResponse(
            "_quick_reply_rows.html", {"request": request, "replies": [], "error": "اختر مشروعاً أولاً"}
        )
    tenant = await get_tenant_by_api_key(session=session, api_key=tenant_api_key)
    if not tenant:
        return templates.TemplateResponse(
            "_quick_reply_rows.html", {"request": request, "replies": [], "error": "مفتاح API غير صالح"}
        )
    replies = await list_quick_replies_for_tenant(session=session, tenant_id=tenant.id)
    return templates.TemplateResponse("_quick_reply_rows.html", {"request": request, "replies": replies, "tenant": tenant})


@router.post("/quick-replies", response_class=HTMLResponse)
async def create_quick_reply_web(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    form = await request.form()
    tenant_api_key = form.get("tenant_api_key", "").strip()
    title = form.get("title", "").strip()
    payload_text = form.get("payload_text", "").strip()
    sort_order = int(form.get("sort_order", "0") or "0")
    is_active = form.get("is_active", "true").lower() == "true"
    
    if not tenant_api_key:
        return templates.TemplateResponse(
            "_quick_reply_rows.html", {"request": request, "replies": [], "error": "مفتاح API مطلوب"}
        )
    
    tenant = await get_tenant_by_api_key(session=session, api_key=tenant_api_key)
    if not tenant:
        return templates.TemplateResponse(
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
    return templates.TemplateResponse(
        "_quick_reply_rows.html", {"request": request, "replies": replies, "tenant": tenant}, status_code=status.HTTP_201_CREATED
    )


@router.post("/quick-replies/{reply_id}/delete", response_class=HTMLResponse)
async def delete_quick_reply_web(
    request: Request,
    reply_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    form = await request.form()
    tenant_api_key = form.get("tenant_api_key", "").strip()
    
    tenant = await get_tenant_by_api_key(session=session, api_key=tenant_api_key)
    if not tenant:
        return templates.TemplateResponse(
            "_quick_reply_rows.html", {"request": request, "replies": [], "error": "مفتاح API غير صالح"}
        )
    
    reply = await get_quick_reply_by_id(session=session, quick_reply_id=reply_id)
    if reply and reply.tenant_id == tenant.id:
        await delete_quick_reply(session=session, quick_reply=reply)
    
    replies = await list_quick_replies_for_tenant(session=session, tenant_id=tenant.id)
    return templates.TemplateResponse("_quick_reply_rows.html", {"request": request, "replies": replies, "tenant": tenant})


# ============ RULES (Scripted Responses) ============
@router.get("/rules", response_class=HTMLResponse)
async def rules_page(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    tenants = await list_tenants(session=session)
    return templates.TemplateResponse("rules.html", {"request": request, "tenants": tenants})


@router.get("/rules/rows", response_class=HTMLResponse)
async def rules_rows(
    request: Request,
    tenant_api_key: str = "",
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    if not tenant_api_key:
        return templates.TemplateResponse(
            "_rule_rows.html", {"request": request, "rules": [], "error": "اختر مشروعاً أولاً"}
        )
    tenant = await get_tenant_by_api_key(session=session, api_key=tenant_api_key)
    if not tenant:
        return templates.TemplateResponse(
            "_rule_rows.html", {"request": request, "rules": [], "error": "مفتاح API غير صالح"}
        )
    rules = await list_active_scripted_responses(session=session, tenant_id=tenant.id)
    return templates.TemplateResponse("_rule_rows.html", {"request": request, "rules": rules, "tenant": tenant})


@router.post("/rules", response_class=HTMLResponse)
async def create_rule_web(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    form = await request.form()
    tenant_api_key = form.get("tenant_api_key", "").strip()
    trigger_keyword = form.get("trigger_keyword", "").strip()
    response_text = form.get("response_text", "").strip()
    is_active = form.get("is_active", "true").lower() == "true"
    
    if not tenant_api_key:
        return templates.TemplateResponse(
            "_rule_rows.html", {"request": request, "rules": [], "error": "مفتاح API مطلوب"}
        )
    
    tenant = await get_tenant_by_api_key(session=session, api_key=tenant_api_key)
    if not tenant:
        return templates.TemplateResponse(
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
    return templates.TemplateResponse(
        "_rule_rows.html", {"request": request, "rules": rules, "tenant": tenant}, status_code=status.HTTP_201_CREATED
    )


@router.post("/rules/{rule_id}/delete", response_class=HTMLResponse)
async def delete_rule_web(
    request: Request,
    rule_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    form = await request.form()
    tenant_api_key = form.get("tenant_api_key", "").strip()
    
    tenant = await get_tenant_by_api_key(session=session, api_key=tenant_api_key)
    if not tenant:
        return templates.TemplateResponse(
            "_rule_rows.html", {"request": request, "rules": [], "error": "مفتاح API غير صالح"}
        )
    
    rule = await get_scripted_response_by_id(session=session, scripted_response_id=rule_id)
    if rule and rule.tenant_id == tenant.id:
        await delete_scripted_response(session=session, scripted_response=rule)
    
    rules = await list_active_scripted_responses(session=session, tenant_id=tenant.id)
    return templates.TemplateResponse("_rule_rows.html", {"request": request, "rules": rules, "tenant": tenant})


# ============ LEADS ============
@router.get("/leads", response_class=HTMLResponse)
async def leads_page(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    tenants = await list_tenants(session=session)
    return templates.TemplateResponse("leads.html", {"request": request, "tenants": tenants})


@router.get("/leads/rows", response_class=HTMLResponse)
async def leads_rows(
    request: Request,
    tenant_api_key: str = "",
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    if not tenant_api_key:
        return templates.TemplateResponse(
            "_lead_rows.html", {"request": request, "leads": [], "error": "اختر مشروعاً أولاً"}
        )
    tenant = await get_tenant_by_api_key(session=session, api_key=tenant_api_key)
    if not tenant:
        return templates.TemplateResponse(
            "_lead_rows.html", {"request": request, "leads": [], "error": "مفتاح API غير صالح"}
        )
    leads = await list_leads(session=session, tenant_id=tenant.id)
    return templates.TemplateResponse("_lead_rows.html", {"request": request, "leads": leads, "tenant": tenant})


# ============ CHAT LOGS ============
@router.get("/chatlogs", response_class=HTMLResponse)
async def chatlogs_page(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    tenants = await list_tenants(session=session)
    return templates.TemplateResponse("chatlogs.html", {"request": request, "tenants": tenants})


@router.get("/chatlogs/rows", response_class=HTMLResponse)
async def chatlogs_rows(
    request: Request,
    tenant_api_key: str = "",
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    if not tenant_api_key:
        return templates.TemplateResponse(
            "_chatlog_rows.html", {"request": request, "logs": [], "error": "اختر مشروعاً أولاً"}
        )
    tenant = await get_tenant_by_api_key(session=session, api_key=tenant_api_key)
    if not tenant:
        return templates.TemplateResponse(
            "_chatlog_rows.html", {"request": request, "logs": [], "error": "مفتاح API غير صالح"}
        )
    logs = await list_chat_logs_for_tenant(session=session, tenant_id=tenant.id, limit=200)
    return templates.TemplateResponse("_chatlog_rows.html", {"request": request, "logs": logs, "tenant": tenant})


# ============ SETTINGS ============
@router.get("/settings", response_class=HTMLResponse)
async def settings_page(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    tenants = await list_tenants(session=session)
    return templates.TemplateResponse("settings.html", {"request": request, "tenants": tenants})


@router.get("/settings/data", response_class=HTMLResponse)
async def settings_data(
    request: Request,
    tenant_api_key: str = "",
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    if not tenant_api_key:
        return templates.TemplateResponse(
            "_settings_form.html",
            {"request": request, "tenant": None, "error": "اختر مشروعاً أولاً"},
        )
    tenant = await get_tenant_by_api_key(session=session, api_key=tenant_api_key)
    if not tenant:
        return templates.TemplateResponse(
            "_settings_form.html",
            {"request": request, "tenant": None, "error": "مفتاح API غير صالح"},
        )
    return templates.TemplateResponse("_settings_form.html", {"request": request, "tenant": tenant})


@router.post("/settings/update", response_class=HTMLResponse)
async def update_settings_web(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    form = await request.form()
    tenant_api_key = form.get("tenant_api_key", "").strip()
    system_prompt = form.get("system_prompt", "").strip()
    webhook_url = form.get("webhook_url", "").strip()
    
    if not tenant_api_key:
        return templates.TemplateResponse(
            "_settings_form.html",
            {"request": request, "tenant": None, "error": "مفتاح API مطلوب"},
        )
    
    tenant = await get_tenant_by_api_key(session=session, api_key=tenant_api_key)
    if not tenant:
        return templates.TemplateResponse(
            "_settings_form.html",
            {"request": request, "tenant": None, "error": "مفتاح API غير صالح"},
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
        {"request": request, "tenant": tenant, "success": "تم حفظ الإعدادات بنجاح ✓"},
    )


# ============ TEST CHAT ============
@router.get("/test-chat", response_class=HTMLResponse)
async def test_chat_page(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    tenants = await list_tenants(session=session)
    return templates.TemplateResponse("test_chat.html", {"request": request, "tenants": tenants})


@router.post("/test-chat/send", response_class=HTMLResponse)
async def send_test_message(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    """Process test chat message and return AI response"""
    form = await request.form()
    tenant_api_key = form.get("tenant_api_key", "").strip()
    message = form.get("message", "").strip()
    
    if not tenant_api_key or not message:
        return HTMLResponse(
            '<div class="text-red-400 text-sm">الرجاء اختيار مشروع وكتابة رسالة</div>'
        )
    
    tenant = await get_tenant_by_api_key(session=session, api_key=tenant_api_key)
    if not tenant:
        return HTMLResponse(
            '<div class="text-red-400 text-sm">مفتاح API غير صالح</div>'
        )
    
    # Import chat service
    from app.services.chat_service import process_message
    
    try:
        # Process the message through AI
        response = await process_message(
            session=session,
            tenant_id=tenant.id,
            channel="test",
            sender_id="test_user",
            message_text=message,
        )
        
        return templates.TemplateResponse(
            "_chat_message.html",
            {
                "request": request,
                "user_message": message,
                "bot_response": response,
                "timestamp": datetime.now().strftime("%H:%M"),
            }
        )
    except Exception as e:
        return HTMLResponse(
            f'<div class="text-red-400 text-sm">خطأ: {str(e)}</div>'
        )


# ============ WIDGET GENERATOR ============
@router.get("/widget", response_class=HTMLResponse)
async def widget_page(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    tenants = await list_tenants(session=session)
    return templates.TemplateResponse("widget.html", {"request": request, "tenants": tenants})


@router.get("/widget/generate", response_class=HTMLResponse)
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
    
    return templates.TemplateResponse(
        "_widget_code.html",
        {"request": request, "tenant": tenant, "api_key": tenant_api_key, "base_url": base_url}
    )


# ============ WIDGET EMBED ENDPOINT ============
@router.get("/embed/{api_key}", response_class=HTMLResponse)
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
    
    return templates.TemplateResponse(
        "embed_widget.html",
        {"request": request, "tenant": tenant, "api_key": api_key, "base_url": base_url}
    )


@router.post("/embed/chat", response_class=HTMLResponse)
async def widget_chat(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    """Handle widget chat messages"""
    form = await request.form()
    api_key = form.get("api_key", "").strip()
    message = form.get("message", "").strip()
    session_id = form.get("session_id", "").strip()
    
    tenant = await get_tenant_by_api_key(session=session, api_key=api_key)
    if not tenant:
        return HTMLResponse('<div class="widget-error">Invalid configuration</div>')
    
    from app.services.chat_service import process_message
    
    try:
        response = await process_message(
            session=session,
            tenant_id=tenant.id,
            channel="widget",
            sender_id=session_id or f"widget_{secrets.token_hex(8)}",
            message_text=message,
        )
        return HTMLResponse(f'<div class="bot-message">{response}</div>')
    except Exception as e:
        return HTMLResponse(f'<div class="widget-error">Error: {str(e)}</div>')
