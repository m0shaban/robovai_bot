# 🏗️ RoboVAI Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                         USER/CLIENT                          │
│                    (Browser / Chat App)                      │
└────────────────┬───────────────────────┬────────────────────┘
                 │                       │
                 │ HTTPS                 │ Webhook
                 ▼                       ▼
┌────────────────────────────────────────────────────────────┐
│                     FASTAPI APPLICATION                      │
│                    (Single Python Process)                   │
│                                                              │
│  ┌────────────────┐  ┌──────────────┐  ┌────────────────┐  │
│  │   UI Router    │  │  API Router  │  │ Webhook Router │  │
│  │  (HTMX+HTML)   │  │   (/api/v1)  │  │  (/webhooks)   │  │
│  └────────┬───────┘  └──────┬───────┘  └────────┬───────┘  │
│           │                  │                   │           │
│           └──────────────────┼───────────────────┘           │
│                              │                               │
│           ┌──────────────────▼──────────────────┐            │
│           │      Services Layer                 │            │
│           │  - chat_service.py (AI logic)       │            │
│           │  - meta_service.py (Meta API)       │            │
│           │  - telegram_service.py              │            │
│           │  - channel_dispatcher.py            │            │
│           │  - lead_service.py                  │            │
│           └──────────────────┬──────────────────┘            │
│                              │                               │
│           ┌──────────────────▼──────────────────┐            │
│           │      CRUD Layer (Database Ops)      │            │
│           │  - tenant.py, channel_integration   │            │
│           │  - quick_reply, scripted_response   │            │
│           │  - lead, chat_log                   │            │
│           └──────────────────┬──────────────────┘            │
│                              │                               │
│           ┌──────────────────▼──────────────────┐            │
│           │  SQLAlchemy ORM (Async)             │            │
│           │  - Models (tenant, lead, etc.)      │            │
│           │  - AsyncSession                     │            │
│           └──────────────────┬──────────────────┘            │
└───────────────────────────────┼───────────────────────────────┘
                                │
                                ▼
              ┌──────────────────────────────────┐
              │      PostgreSQL Database         │
              │  - Tenants                       │
              │  - Channel Integrations          │
              │  - Quick Replies                 │
              │  - Scripted Responses            │
              │  - Leads                         │
              │  - Chat Logs                     │
              └──────────────────────────────────┘
                                │
                                ▼
              ┌──────────────────────────────────┐
              │    External Services             │
              │  - Groq/OpenAI (LLM)            │
              │  - Telegram Bot API              │
              │  - Meta Graph API                │
              │  - Customer Webhooks             │
              └──────────────────────────────────┘
```

---

## Data Flow Examples

### 1. User Opens Dashboard (HTMX)
```
Browser
  │
  │ GET /ui/tenants
  ▼
FastAPI UI Router
  │
  │ query database
  ▼
CRUD Layer (tenant.list_tenants)
  │
  ▼
PostgreSQL
  │
  ▼
Templates (tenants.html) ← render with data
  │
  ▼
Browser (displays HTML)
```

### 2. Webhook from Telegram
```
Telegram Bot API
  │
  │ POST /webhooks/telegram/<tenant_id>
  ▼
FastAPI Webhook Router
  │
  │ verify tenant
  ▼
Channel Dispatcher
  │
  │ route to handler
  ▼
Telegram Service
  │
  ├─► Extract message
  ├─► Check scripted responses
  ├─► Send to Chat Service (if no match)
  │
  ▼
Chat Service (AI Logic)
  │
  ├─► Check context window
  ├─► Load system prompt
  ├─► Call LLM (Groq/OpenAI)
  ├─► Save to chat_logs
  │
  ▼
Send Response via Telegram API
```

### 3. Create Quick Reply (HTMX)
```
Browser (clicks "Add Quick Reply")
  │
  │ POST /ui/quick-replies (HTMX)
  ▼
FastAPI UI Router
  │
  │ validate tenant API key
  ▼
CRUD Layer (quick_reply.create)
  │
  ▼
PostgreSQL (INSERT)
  │
  ▼
Templates (_quick_reply_rows.html) ← render new row only
  │
  ▼
Browser (HTMX swaps in new row - NO page reload!)
```

---

## Technology Stack Details

### Backend
- **FastAPI** (v0.110+) - Modern async web framework
- **Uvicorn** - ASGI server (production-ready)
- **SQLAlchemy 2.0** - ORM with async support
- **asyncpg** - Fast PostgreSQL driver
- **Alembic** - Database migrations
- **Pydantic** - Data validation

### Frontend
- **Jinja2** - Server-side templating
- **HTMX 1.9.12** - Partial page updates via HTML
- **Tailwind CSS** - Utility-first styling (CDN)
- **No JavaScript frameworks** - Just HTMX + vanilla JS

### AI/LLM
- **Groq** (default) - Fast inference
- **OpenAI** - GPT models
- **Azure OpenAI** - Enterprise GPT
- **Anthropic** - Claude models

### Deployment
- **Render** - PaaS with free tier
- **PostgreSQL** - Managed database
- **Git** - Source control + CI/CD trigger

---

## File Structure Map

```
robovai-bot/
│
├── app/
│   ├── main.py              # FastAPI app entry (uvicorn serves this)
│   ├── api/                 # REST API endpoints
│   │   ├── v1/routers/
│   │   │   ├── admin.py     # Tenant management
│   │   │   └── chat.py      # Chat operations
│   │   └── webhooks.py      # Channel webhooks
│   │
│   ├── ui/
│   │   └── web.py           # HTMX dashboard router
│   │
│   ├── templates/           # HTML templates
│   │   ├── base.html        # Layout + navigation
│   │   ├── onboarding.html  # First-time user welcome
│   │   ├── tenants.html     # Tenant management page
│   │   ├── channels.html    # Channel integrations
│   │   ├── quick_replies.html
│   │   ├── rules.html       # Scripted responses
│   │   ├── leads.html       # Customer leads
│   │   ├── chatlogs.html    # Conversation history
│   │   ├── settings.html    # System config
│   │   └── _*.html          # Partials for HTMX swaps
│   │
│   ├── services/            # Business logic
│   │   ├── chat_service.py  # AI conversation handling
│   │   ├── meta_service.py  # WhatsApp/Messenger
│   │   ├── telegram_service.py
│   │   └── channel_dispatcher.py
│   │
│   ├── crud/                # Database operations
│   │   ├── tenant.py
│   │   ├── channel_integration.py
│   │   ├── quick_reply.py
│   │   ├── scripted_response.py
│   │   ├── lead.py
│   │   └── chat_log.py
│   │
│   ├── models/              # SQLAlchemy models
│   ├── schemas/             # Pydantic schemas
│   └── core/                # Config, settings
│
├── migrations/              # Alembic database versions
├── docs/                    # Documentation
├── start.py                 # Platform launcher script
├── render.yaml              # Render deployment config
├── requirements.txt         # Python dependencies
├── .env.example             # Environment template
└── PRODUCTION_READY.md      # This checklist!
```

---

## Port & URL Map

### Local Development
| Service | URL | Purpose |
|---------|-----|---------|
| Dashboard | http://localhost:8000/ui | HTMX admin interface |
| API Docs | http://localhost:8000/docs | Interactive API explorer |
| Health Check | http://localhost:8000/health | Status endpoint |
| Tenant API | http://localhost:8000/api/v1/* | REST API (needs API key) |
| Webhooks | http://localhost:8000/webhooks/* | Channel callbacks |

### Production (Render)
| Service | URL | Purpose |
|---------|-----|---------|
| Dashboard | https://your-app.onrender.com/ui | Admin interface |
| Webhook (Telegram) | https://your-app.onrender.com/webhooks/telegram/{tenant_id} | Bot callback |
| Webhook (Meta) | https://your-app.onrender.com/webhooks/meta | WhatsApp/Messenger |
| API | https://your-app.onrender.com/api/v1/* | REST endpoints |

---

## Security Architecture

### Authentication Layers
1. **Admin Operations** (Tenants page):
   - Protected by `ADMIN_PASSWORD` env var
   - Required for tenant create/delete/update

2. **Tenant Operations** (All other pages):
   - Protected by tenant API key
   - Each tenant has unique key
   - Keys can be rotated

3. **Webhook Verification**:
   - Telegram: Uses tenant_id in URL + bot token validation
   - Meta: Uses verify_token for challenge handshake

### Data Isolation
- Each tenant has isolated:
  - Channel integrations
  - Quick replies
  - Scripted responses
  - Leads
  - Chat logs
  - Settings

### Environment Secrets
- Never commit `.env` to git
- Use Render environment variables UI
- Rotate API keys regularly

---

## Performance Considerations

### Database Optimization
- Indexes on `tenant_id`, `created_at`
- Connection pooling via asyncpg
- Lazy loading for relationships

### API Response Times
- Target: < 200ms for HTMX swaps
- Target: < 1s for AI responses
- Use async/await throughout

### Scalability
- Horizontal: Add more Render instances
- Vertical: Upgrade Render plan
- Database: Upgrade PostgreSQL plan

### Monitoring
- Render provides built-in logs
- Add custom logging for:
  - Failed webhook deliveries
  - LLM API errors
  - Database connection issues

---

## Deployment Workflow

```
Developer
  │
  │ git push
  ▼
GitHub Repository
  │
  │ webhook trigger
  ▼
Render Platform
  │
  ├─► Detect render.yaml
  ├─► Create PostgreSQL instance
  ├─► Run migrations (alembic upgrade head)
  ├─► Build Docker image (or Python buildpack)
  ├─► Start web service (uvicorn)
  ├─► Health check (/health)
  │
  ▼
Production URL
  │
  ▼
Users access https://your-app.onrender.com
```

### Automatic Updates
- Push to `main` branch → Auto-redeploy
- Zero-downtime deployments
- Rollback available in Render UI

---

## HTMX Magic Explained

Traditional web apps:
```
User clicks button → Full page reload → Server sends entire HTML → Browser repaints everything
```

HTMX approach:
```
User clicks button → AJAX request → Server sends only changed HTML → HTMX swaps specific part
```

### Example: Adding a Quick Reply
```html
<!-- Button with HTMX attributes -->
<button 
  hx-post="/ui/quick-replies"
  hx-target="#quick-replies-table"
  hx-swap="afterbegin">
  Add Quick Reply
</button>

<!-- HTMX does: -->
1. Intercept button click
2. POST form data to /ui/quick-replies
3. Server returns <tr>...</tr> (just the new row!)
4. HTMX inserts it at top of table
5. NO FULL PAGE RELOAD! ⚡
```

Benefits:
- Faster (only sends HTML diff)
- Simpler (no JSON parsing, no React/Vue)
- SEO-friendly (still server-rendered)
- Progressive enhancement (works with JS disabled)

---

## Next Steps

1. **Local Testing**: Run `python start.py` and test all features
2. **Environment Setup**: Copy `.env.example` → `.env` and configure
3. **Database Migrations**: Run `alembic upgrade head`
4. **Deploy to Render**: Use `render.yaml` for one-click setup
5. **Configure Channels**: Add bot tokens and webhook URLs
6. **Test Live Bot**: Send messages and verify responses
7. **Monitor**: Check Render logs for any issues
8. **Scale**: Upgrade plans as usage grows

---

**Status**: ✅ Architecture Documented & Production Ready
