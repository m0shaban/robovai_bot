from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.api.v1.api import api_router
from app.api.health import router as health_router
from app.api.webhooks import router as webhooks_router
from app.ui.web import router as ui_router
from app.ui.auth_routes import auth_ui_router
from app.core.config import settings
from app.db.session import engine


def _parse_cors_origins(value: str) -> list[str]:
    raw = (value or "").strip()
    if not raw:
        return []
    if raw == "*":
        return ["*"]
    return [o.strip() for o in raw.split(",") if o.strip()]


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure models are imported before creating tables.
    import app.models  # noqa: F401
    from app.models.base import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Auto-create super admin if none exists
    await _create_default_super_admin()

    yield


async def _create_default_super_admin():
    """Create a default super admin if none exists (for fresh deployments)."""
    import os
    from app.db.session import async_session_maker
    from app.crud.user import count_super_admins, create_super_admin, get_user_by_email

    # Get credentials from environment variables
    admin_email = os.getenv("SUPER_ADMIN_EMAIL", "admin@robovai.com")
    admin_password = os.getenv("SUPER_ADMIN_PASSWORD", "")
    admin_name = os.getenv("SUPER_ADMIN_NAME", "Super Admin")

    if not admin_password:
        # Use ADMIN_PASSWORD as fallback for backwards compatibility
        admin_password = os.getenv("ADMIN_PASSWORD", "")

    if not admin_password:
        print("⚠️  No SUPER_ADMIN_PASSWORD set, skipping auto-creation of super admin")
        return

    try:
        async with async_session_maker() as session:
            # Check if super admin already exists
            existing_count = await count_super_admins(session)
            if existing_count > 0:
                print(f"✓ Super admin already exists ({existing_count} found)")
                return

            # Check if email is already used
            existing_user = await get_user_by_email(session, admin_email)
            if existing_user:
                print(f"✓ User with email {admin_email} already exists")
                return

            # Create super admin
            user = await create_super_admin(
                session,
                email=admin_email,
                password=admin_password,
                full_name=admin_name,
            )
            print(f"✅ Super Admin created: {user.email}")
    except Exception as e:
        print(f"⚠️  Could not create super admin: {e}")


app = FastAPI(title="RoboVAI Multi-Tenant Chatbot", lifespan=lifespan)

# Mount static files
static_path = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

# Root redirect to UI Landing Page
from fastapi.responses import RedirectResponse


@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/ui/welcome")


origins = _parse_cors_origins(settings.cors_allow_origins)

# If allowing '*', credentials must be False.
allow_credentials = False if "*" in origins else True

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or [],
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API router with /api prefix so paths are /api/v1/...
app.include_router(api_router, prefix="/api")
app.include_router(health_router)
app.include_router(webhooks_router)
app.include_router(ui_router)
app.include_router(auth_ui_router)
