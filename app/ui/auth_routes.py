"""
Authentication UI routes.
Handles web-based authentication flows (registration, login, password reset).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from app.api.deps import get_db_session
from app.crud.user import (
    create_user,
    get_user_by_email,
    get_user_by_reset_token,
    generate_reset_token,
    update_user_password,
    user_exists,
)
from app.models.user import UserRole
from app.services.auth_service import (
    AuthError,
    authenticate_user,
    create_token_pair,
    get_current_user,
)
from app.crud.user import update_last_login
from app.services.email_service import email_service

# Templates
jinja_templates = Jinja2Templates(directory="app/templates")

# Router
auth_ui_router = APIRouter(prefix="/ui/auth", tags=["auth-ui"])


# ==================== Registration ====================

@auth_ui_router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """Show registration form."""
    return jinja_templates.TemplateResponse(
        "auth/register.html",
        {"request": request}
    )


@auth_ui_router.post("/register", response_class=HTMLResponse)
async def register_submit(
    request: Request,
    full_name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(None),
    password: str = Form(...),
    confirm_password: str = Form(...),
    terms: bool = Form(False),
    session: AsyncSession = Depends(get_db_session),
):
    """Process registration form."""
    error = None
    
    # Validate
    if password != confirm_password:
        error = "كلمتا المرور غير متطابقتان"
    elif len(password) < 8:
        error = "كلمة المرور يجب أن تكون 8 أحرف على الأقل"
    elif not terms:
        error = "يجب الموافقة على شروط الاستخدام"
    
    if error:
        return jinja_templates.TemplateResponse(
            "auth/register.html",
            {"request": request, "error": error}
        )

    # Check if user exists
    existing_user = await get_user_by_email(session, email)
    if existing_user:
        if existing_user.is_verified:
            return jinja_templates.TemplateResponse(
                "auth/register.html",
                {"request": request, "error": "البريد الإلكتروني مسجل مسبقاً. يرجى تسجيل الدخول."}
            )
        else:
            # Resend verification email
            from app.crud.user import generate_verification_token
            token = await generate_verification_token(session, existing_user)
            verification_url = f"{request.base_url}ui/auth/verify-email?token={token}"
            
            try:
                sent = await email_service.send_verification_email(
                    to_email=existing_user.email,
                    verification_url=verification_url,
                    user_name=existing_user.full_name,
                )
                if sent:
                    print(f"✅ Verification email resent to {email}")
                else:
                    print(f"⚠️  Email service returned False for {email}")
                    print(f"[DEV] Verification link: {verification_url}")
            except Exception as e:
                print(f"⚠️  Failed to resend verification email: {e}")
                print(f"[DEV] Verification link: {verification_url}")
            
            return jinja_templates.TemplateResponse(
                "auth/register.html",
                {
                    "request": request,
                    "success": True,
                    "message": "الحساب موجود ولكنه غير مفعل. تم إرسال رابط تفعيل جديد إلى بريدك الإلكتروني."
                }
            )
    
    # Create user
    try:
        user = await create_user(
            session,
            email=email,
            password=password,
            full_name=full_name,
            phone=phone,
            role=UserRole.AGENT,  # Default role
            is_verified=False,  # Require email verification
        )
        
        # Send verification email
        from app.crud.user import generate_verification_token
        token = await generate_verification_token(session, user)
        verification_url = f"{request.base_url}ui/auth/verify-email?token={token}"
        
        try:
            sent = await email_service.send_verification_email(
                to_email=user.email,
                verification_url=verification_url,
                user_name=user.full_name,
            )
            if sent:
                print(f"✅ Verification email sent to {email}")
            else:
                print(f"⚠️  Email service returned False for {email}")
                print(f"[DEV] Verification link: {verification_url}")
        except Exception as e:
            print(f"⚠️  Failed to send verification email: {e}")
            print(f"[DEV] Verification link: {verification_url}")
        
        # Show success message (don't auto-login until verified)
        return jinja_templates.TemplateResponse(
            "auth/register.html",
            {
                "request": request,
                "success": True,
                "message": "تم إنشاء الحساب بنجاح! يرجى التحقق من بريدك الإلكتروني لتفعيل الحساب."
            }
        )
        
    except Exception as e:
        return jinja_templates.TemplateResponse(
            "auth/register.html",
            {"request": request, "error": f"حدث خطأ: {str(e)}"}
        )


# ==================== Login ====================

@auth_ui_router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: str = None, success: str = None):
    """Show login form."""
    return jinja_templates.TemplateResponse(
        "auth/login.html",
        {
            "request": request,
            "error": error,
            "success": success,
            "show_admin_login": True,  # Show link to simple admin login
        }
    )


@auth_ui_router.post("/login", response_class=HTMLResponse)
async def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    remember_me: bool = Form(False),
    session: AsyncSession = Depends(get_db_session),
):
    """Process login form."""
    # Authenticate
    user = await authenticate_user(session, email, password)
    
    if not user:
        # Check specific failure reasons for better feedback
        existing_user = await get_user_by_email(session, email)
        error_msg = "البريد الإلكتروني أو كلمة المرور غير صحيحة"
        
        if existing_user:
            if not existing_user.is_active:
                error_msg = "تم تعطيل هذا الحساب. يرجى الاتصال بالدعم."
            # Note: We don't reveal if password is wrong for security, 
            # but we do help with account status issues.
        
        return jinja_templates.TemplateResponse(
            "auth/login.html",
            {
                "request": request,
                "error": error_msg,
                "email": email,
                "show_admin_login": True,
            }
        )
    
    # Check verification status
    if not user.is_verified:
        return jinja_templates.TemplateResponse(
            "auth/login.html",
            {
                "request": request,
                "error": "يرجى تفعيل حسابك أولاً. تحقق من بريدك الإلكتروني.",
                "email": email,
                "show_admin_login": True,
            }
        )
    
    # Update last login
    await update_last_login(session, user)
    
    # Create tokens
    tokens = create_token_pair(user, remember_me)
    
    # Redirect to dashboard
    response = RedirectResponse(
        url="/ui/dashboard",
        status_code=status.HTTP_303_SEE_OTHER
    )
    
    # Set cookies
    max_age = 60 * 60 * 24 * 30 if remember_me else tokens.expires_in
    response.set_cookie(
        key="access_token",
        value=tokens.access_token,
        httponly=True,
        max_age=max_age,
        samesite="lax"
    )
    response.set_cookie(
        key="refresh_token",
        value=tokens.refresh_token,
        httponly=True,
        max_age=60 * 60 * 24 * (30 if remember_me else 7),
        samesite="lax"
    )
    
    return response


# ==================== Logout ====================

@auth_ui_router.get("/logout")
async def logout():
    """Logout user."""
    response = RedirectResponse(
        url="/ui/auth/login",
        status_code=status.HTTP_303_SEE_OTHER
    )
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return response


# ==================== Password Reset ====================

@auth_ui_router.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password_page(request: Request):
    """Show forgot password form."""
    return jinja_templates.TemplateResponse(
        "auth/forgot_password.html",
        {"request": request}
    )


@auth_ui_router.post("/forgot-password", response_class=HTMLResponse)
async def forgot_password_submit(
    request: Request,
    email: str = Form(...),
    session: AsyncSession = Depends(get_db_session),
):
    """Process forgot password form."""
    user = await get_user_by_email(session, email)
    
    if user:
        # Generate reset token
        token = await generate_reset_token(session, user)
        
        # Send email with reset link
        reset_url = f"{request.base_url}ui/auth/reset-password?token={token}"
        try:
            await email_service.send_password_reset_email(
                to_email=user.email,
                reset_url=reset_url,
                user_name=user.full_name,
            )
            print(f"✅ Password reset email sent to {email}")
        except Exception as e:
            print(f"⚠️  Failed to send email: {e}")
            print(f"[DEV] Password reset token for {email}: {token}")
    
    # Always show success (don't reveal if email exists)
    return jinja_templates.TemplateResponse(
        "auth/forgot_password.html",
        {"request": request, "success": True}
    )


@auth_ui_router.get("/reset-password", response_class=HTMLResponse)
async def reset_password_page(
    request: Request,
    token: str,
    session: AsyncSession = Depends(get_db_session),
):
    """Show reset password form."""
    # Verify token is valid
    user = await get_user_by_reset_token(session, token)
    
    if not user:
        return jinja_templates.TemplateResponse(
            "auth/reset_password.html",
            {"request": request, "token_invalid": True}
        )
    
    return jinja_templates.TemplateResponse(
        "auth/reset_password.html",
        {"request": request, "token": token}
    )


@auth_ui_router.post("/reset-password", response_class=HTMLResponse)
async def reset_password_submit(
    request: Request,
    token: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    session: AsyncSession = Depends(get_db_session),
):
    """Process reset password form."""
    # Validate passwords match
    if password != confirm_password:
        return jinja_templates.TemplateResponse(
            "auth/reset_password.html",
            {"request": request, "token": token, "error": "كلمتا المرور غير متطابقتان"}
        )
    
    # Verify token and get user
    user = await get_user_by_reset_token(session, token)
    
    if not user:
        return jinja_templates.TemplateResponse(
            "auth/reset_password.html",
            {"request": request, "token_invalid": True}
        )
    
    # Update password
    await update_user_password(session, user, password)
    
    # Redirect to login with success message
    return RedirectResponse(
        url="/ui/auth/login?success=تم+تغيير+كلمة+المرور+بنجاح",
        status_code=status.HTTP_303_SEE_OTHER
    )


# ==================== Email Verification ====================

@auth_ui_router.get("/verify-email", response_class=HTMLResponse)
async def verify_email_page(
    request: Request,
    token: str,
    session: AsyncSession = Depends(get_db_session),
):
    """Verify email with token."""
    from app.crud.user import get_user_by_verification_token, verify_user_email
    
    user = await get_user_by_verification_token(session, token)
    
    if not user:
        return jinja_templates.TemplateResponse(
            "auth/verify_email.html",
            {"request": request, "error": "رمز التحقق غير صالح أو منتهي الصلاحية"}
        )
    
    await verify_user_email(session, user)
    
    return jinja_templates.TemplateResponse(
        "auth/verify_email.html",
        {"request": request, "success": True}
    )
