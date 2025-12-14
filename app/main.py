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

    yield


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

app.include_router(api_router)
app.include_router(health_router)
app.include_router(webhooks_router)
app.include_router(ui_router)
app.include_router(auth_ui_router)
