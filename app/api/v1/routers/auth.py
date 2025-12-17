"""
Authentication API router.
Handles registration, login, password reset, and user management.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.models.user import User, UserRole
from app.schemas.auth import (
    EmailVerificationRequest,
    PasswordChangeRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    ResendVerificationRequest,
    TokenResponse,
    UserCreateRequest,
    UserListResponse,
    UserLoginRequest,
    UserLoginResponse,
    UserProfile,
    UserProfileUpdate,
    UserRegisterRequest,
    UserRegisterResponse,
    UserUpdateRequest,
)
from app.services.auth_service import (
    AuthError,
    get_current_user,
    login_user,
    refresh_tokens,
    register_user,
    request_password_reset,
    require_role,
    reset_password,
    resend_verification,
    verify_email,
)
from app.crud.user import (
    create_user,
    delete_user,
    get_user_by_id,
    list_users,
    update_user,
    update_user_password,
)
from app.core.security import verify_password

router = APIRouter(prefix="/auth", tags=["authentication"])


# ==================== Helper: Get Current User ====================


async def get_current_user_dependency(
    token: str = None,
    session: AsyncSession = Depends(get_db_session),
) -> User:
    """Dependency to get current authenticated user."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="لم يتم تقديم رمز المصادقة",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        return await get_current_user(session, token)
    except AuthError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message,
            headers={"WWW-Authenticate": "Bearer"},
        )


# ==================== Public Routes ====================


@router.post(
    "/register",
    response_model=UserRegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    data: UserRegisterRequest,
    session: AsyncSession = Depends(get_db_session),
):
    """
    Register a new user account.

    - **email**: Valid email address (unique)
    - **password**: Minimum 8 characters with uppercase, lowercase, and number
    - **full_name**: User's display name
    - **phone**: Optional phone number
    """
    try:
        return await register_user(session, data)
    except AuthError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )


@router.post("/login", response_model=UserLoginResponse)
async def login(
    data: UserLoginRequest,
    session: AsyncSession = Depends(get_db_session),
):
    """
    Authenticate user and get access tokens.

    - **email**: Registered email address
    - **password**: Account password
    - **remember_me**: If true, refresh token lasts 30 days instead of 7
    """
    try:
        return await login_user(session, data)
    except AuthError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message,
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    refresh_token: str,
    session: AsyncSession = Depends(get_db_session),
):
    """
    Refresh access token using refresh token.
    """
    try:
        return await refresh_tokens(session, refresh_token)
    except AuthError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message,
        )


# ==================== Password Reset ====================


@router.post("/password/forgot")
async def forgot_password(
    data: PasswordResetRequest,
    session: AsyncSession = Depends(get_db_session),
):
    """
    Request password reset email.
    """
    message = await request_password_reset(session, data.email)
    return {"message": message}


@router.post("/password/reset")
async def reset_password_confirm(
    data: PasswordResetConfirm,
    session: AsyncSession = Depends(get_db_session),
):
    """
    Reset password using token from email.
    """
    try:
        message = await reset_password(session, data.token, data.new_password)
        return {"message": message}
    except AuthError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )


# ==================== Email Verification ====================


@router.post("/verify-email")
async def verify_email_route(
    data: EmailVerificationRequest,
    session: AsyncSession = Depends(get_db_session),
):
    """
    Verify email address using token.
    """
    try:
        message = await verify_email(session, data.token)
        return {"message": message}
    except AuthError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )


@router.post("/resend-verification")
async def resend_verification_route(
    data: ResendVerificationRequest,
    session: AsyncSession = Depends(get_db_session),
):
    """
    Resend verification email.
    """
    message = await resend_verification(session, data.email)
    return {"message": message}


# ==================== Protected Routes (Require Auth) ====================


@router.get("/me", response_model=UserProfile)
async def get_me(
    token: str,
    session: AsyncSession = Depends(get_db_session),
):
    """
    Get current user profile.
    """
    try:
        user = await get_current_user(session, token)
        return UserProfile(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            avatar_url=user.avatar_url,
            phone=user.phone,
            role=user.role,
            tenant_id=user.tenant_id,
            tenant_name=user.tenant.name if user.tenant else None,
            is_active=user.is_active,
            is_verified=user.is_verified,
            created_at=user.created_at,
            last_login=user.last_login,
        )
    except AuthError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message,
        )


@router.patch("/me", response_model=UserProfile)
async def update_me(
    token: str,
    data: UserProfileUpdate,
    session: AsyncSession = Depends(get_db_session),
):
    """
    Update current user profile.
    """
    try:
        user = await get_current_user(session, token)
        user = await update_user(
            session,
            user,
            full_name=data.full_name,
            phone=data.phone,
            avatar_url=data.avatar_url,
        )
        return UserProfile(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            avatar_url=user.avatar_url,
            phone=user.phone,
            role=user.role,
            tenant_id=user.tenant_id,
            tenant_name=user.tenant.name if user.tenant else None,
            is_active=user.is_active,
            is_verified=user.is_verified,
            created_at=user.created_at,
            last_login=user.last_login,
        )
    except AuthError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message,
        )


@router.post("/me/password")
async def change_password(
    token: str,
    data: PasswordChangeRequest,
    session: AsyncSession = Depends(get_db_session),
):
    """
    Change current user password.
    """
    try:
        user = await get_current_user(session, token)

        # Verify current password
        if not verify_password(data.current_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="كلمة المرور الحالية غير صحيحة",
            )

        await update_user_password(session, user, data.new_password)
        return {"message": "تم تغيير كلمة المرور بنجاح"}
    except AuthError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message,
        )


# ==================== Admin Routes (User Management) ====================


@router.get("/users", response_model=UserListResponse)
async def list_users_route(
    token: str,
    page: int = 1,
    page_size: int = 20,
    search: str = None,
    role: UserRole = None,
    tenant_id: int = None,
    is_active: bool = None,
    session: AsyncSession = Depends(get_db_session),
):
    """
    List users (Admin only).
    """
    try:
        current_user = await get_current_user(session, token)
        require_role(
            current_user, UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.MANAGER
        )

        # Non-super admins can only see their tenant's users
        if current_user.role != UserRole.SUPER_ADMIN:
            tenant_id = current_user.tenant_id

        users, total = await list_users(
            session,
            tenant_id=tenant_id,
            role=role,
            is_active=is_active,
            search=search,
            page=page,
            page_size=page_size,
        )

        total_pages = (total + page_size - 1) // page_size

        return UserListResponse(
            users=[
                UserProfile(
                    id=u.id,
                    email=u.email,
                    full_name=u.full_name,
                    avatar_url=u.avatar_url,
                    phone=u.phone,
                    role=u.role,
                    tenant_id=u.tenant_id,
                    tenant_name=u.tenant.name if u.tenant else None,
                    is_active=u.is_active,
                    is_verified=u.is_verified,
                    created_at=u.created_at,
                    last_login=u.last_login,
                )
                for u in users
            ],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
    except AuthError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message,
        )


@router.post("/users", response_model=UserProfile, status_code=status.HTTP_201_CREATED)
async def create_user_route(
    token: str,
    data: UserCreateRequest,
    session: AsyncSession = Depends(get_db_session),
):
    """
    Create a new user (Admin only).
    """
    try:
        current_user = await get_current_user(session, token)
        require_role(current_user, UserRole.SUPER_ADMIN, UserRole.ADMIN)

        # Non-super admins can only create users for their tenant
        tenant_id = data.tenant_id
        if current_user.role != UserRole.SUPER_ADMIN:
            tenant_id = current_user.tenant_id
            # Non-super admins can't create admins
            if data.role == UserRole.SUPER_ADMIN:
                raise AuthError(
                    "لا يمكنك إنشاء مستخدم بهذه الصلاحية", "PERMISSION_DENIED"
                )

        user = await create_user(
            session,
            email=data.email,
            password=data.password,
            full_name=data.full_name,
            phone=data.phone,
            role=data.role,
            tenant_id=tenant_id,
            is_active=data.is_active,
            is_verified=not data.send_verification_email,
        )

        return UserProfile(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            avatar_url=user.avatar_url,
            phone=user.phone,
            role=user.role,
            tenant_id=user.tenant_id,
            tenant_name=user.tenant.name if user.tenant else None,
            is_active=user.is_active,
            is_verified=user.is_verified,
            created_at=user.created_at,
            last_login=user.last_login,
        )
    except AuthError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message,
        )


@router.get("/users/{user_id}", response_model=UserProfile)
async def get_user_route(
    user_id: int,
    token: str,
    session: AsyncSession = Depends(get_db_session),
):
    """
    Get user by ID (Admin only).
    """
    try:
        current_user = await get_current_user(session, token)
        require_role(
            current_user, UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.MANAGER
        )

        user = await get_user_by_id(session, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="المستخدم غير موجود",
            )

        # Non-super admins can only see their tenant's users
        if (
            current_user.role != UserRole.SUPER_ADMIN
            and user.tenant_id != current_user.tenant_id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="ليس لديك صلاحية عرض هذا المستخدم",
            )

        return UserProfile(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            avatar_url=user.avatar_url,
            phone=user.phone,
            role=user.role,
            tenant_id=user.tenant_id,
            tenant_name=user.tenant.name if user.tenant else None,
            is_active=user.is_active,
            is_verified=user.is_verified,
            created_at=user.created_at,
            last_login=user.last_login,
        )
    except AuthError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message,
        )


@router.patch("/users/{user_id}", response_model=UserProfile)
async def update_user_route(
    user_id: int,
    token: str,
    data: UserUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
):
    """
    Update user (Admin only).
    """
    try:
        current_user = await get_current_user(session, token)
        require_role(current_user, UserRole.SUPER_ADMIN, UserRole.ADMIN)

        user = await get_user_by_id(session, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="المستخدم غير موجود",
            )

        # Non-super admins can only update their tenant's users
        if (
            current_user.role != UserRole.SUPER_ADMIN
            and user.tenant_id != current_user.tenant_id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="ليس لديك صلاحية تعديل هذا المستخدم",
            )

        # Non-super admins can't promote to super admin
        if (
            current_user.role != UserRole.SUPER_ADMIN
            and data.role == UserRole.SUPER_ADMIN
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="لا يمكنك ترقية المستخدم لهذه الصلاحية",
            )

        user = await update_user(
            session,
            user,
            email=data.email,
            full_name=data.full_name,
            phone=data.phone,
            role=data.role,
            tenant_id=(
                data.tenant_id if current_user.role == UserRole.SUPER_ADMIN else None
            ),
            is_active=data.is_active,
            is_verified=data.is_verified,
        )

        return UserProfile(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            avatar_url=user.avatar_url,
            phone=user.phone,
            role=user.role,
            tenant_id=user.tenant_id,
            tenant_name=user.tenant.name if user.tenant else None,
            is_active=user.is_active,
            is_verified=user.is_verified,
            created_at=user.created_at,
            last_login=user.last_login,
        )
    except AuthError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message,
        )


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_route(
    user_id: int,
    token: str,
    session: AsyncSession = Depends(get_db_session),
):
    """
    Delete user (Admin only).
    """
    try:
        current_user = await get_current_user(session, token)
        require_role(current_user, UserRole.SUPER_ADMIN, UserRole.ADMIN)

        user = await get_user_by_id(session, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="المستخدم غير موجود",
            )

        # Can't delete yourself
        if user.id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="لا يمكنك حذف حسابك الخاص",
            )

        # Non-super admins can only delete their tenant's users
        if (
            current_user.role != UserRole.SUPER_ADMIN
            and user.tenant_id != current_user.tenant_id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="ليس لديك صلاحية حذف هذا المستخدم",
            )

        # Can't delete super admin
        if (
            user.role == UserRole.SUPER_ADMIN
            and current_user.role != UserRole.SUPER_ADMIN
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="لا يمكنك حذف مدير النظام",
            )

        await delete_user(session, user)
    except AuthError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message,
        )


# ==================== Email Testing & Configuration ====================


@router.get("/email/config-status")
async def get_email_config_status():
    """
    Get email configuration status (shows if email is properly configured).
    Does NOT reveal sensitive credentials.
    """
    from app.core.config import settings
    from app.services.email_service import email_service
    
    smtp_configured = bool(
        settings.smtp_host 
        and settings.smtp_user 
        and settings.smtp_password
    )
    sendgrid_configured = bool(settings.sendgrid_api_key)
    
    return {
        "email_enabled": smtp_configured or sendgrid_configured,
        "smtp": {
            "configured": smtp_configured,
            "host": settings.smtp_host if smtp_configured else None,
            "port": settings.smtp_port if smtp_configured else None,
            "tls": settings.smtp_tls if smtp_configured else None,
            "user_configured": bool(settings.smtp_user),
            "password_configured": bool(settings.smtp_password),
            "is_gmail": email_service.is_gmail if smtp_configured else False,
        },
        "sendgrid": {
            "configured": sendgrid_configured,
        },
        "from_email": email_service.from_email or "Not configured",
        "from_name": email_service.from_name or "Not configured",
    }


@router.post("/email/test")
async def test_email_sending(
    token: str,
    to_email: str = None,
    session: AsyncSession = Depends(get_db_session),
):
    """
    Send a test email to verify email configuration (Admin only).
    If to_email is not provided, sends to the current user's email.
    """
    try:
        current_user = await get_current_user(session, token)
        require_role(current_user, UserRole.SUPER_ADMIN, UserRole.ADMIN)
        
        from app.services.email_service import email_service
        
        test_to_email = to_email or current_user.email
        
        # Send a simple test email
        html_content = f"""
        <!DOCTYPE html>
        <html dir="rtl" lang="ar">
        <head><meta charset="UTF-8"></head>
        <body style="font-family: Cairo, Arial, sans-serif; background: #f3f4f6; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 12px; padding: 30px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                <h1 style="color: #0891b2; margin-bottom: 20px;">✅ اختبار البريد الإلكتروني</h1>
                <p style="color: #1f2937; font-size: 16px; line-height: 1.6;">
                    مرحباً {current_user.full_name},<br><br>
                    إذا تلقيت هذه الرسالة، فإن إعدادات البريد الإلكتروني تعمل بشكل صحيح! 🎉
                </p>
                <div style="background: #ecfdf5; border: 1px solid #10b981; border-radius: 8px; padding: 15px; margin: 20px 0;">
                    <p style="margin: 0; color: #059669; font-weight: bold;">
                        ✓ تم تأكيد اتصال SMTP بنجاح
                    </p>
                </div>
                <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 30px 0;">
                <p style="color: #9ca3af; font-size: 12px; text-align: center;">
                    © 2025 RoboVAI Solutions - منصة الشات بوت الذكي
                </p>
            </div>
        </body>
        </html>
        """
        
        success = await email_service._send_email(
            to_email=test_to_email,
            subject="🧪 اختبار إعدادات البريد الإلكتروني - RoboVAI",
            html_content=html_content,
        )
        
        if success:
            return {
                "success": True,
                "message": f"تم إرسال رسالة الاختبار بنجاح إلى {test_to_email}",
                "to_email": test_to_email,
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="فشل إرسال البريد الإلكتروني. تحقق من إعدادات SMTP.",
            )
            
    except AuthError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message,
        )
