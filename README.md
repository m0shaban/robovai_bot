# RoboVAI Bot Platform

**Powered by [RoboVAI Solutions](https://robovai.blogspot.com/) - Your Partner in Digital Transformation**

**RoboVAI Bot** is a modern AI-powered chatbot platform designed to automate customer service and drive digital transformation. It is one of the flagship products of RoboVAI Solutions.

> **Created with love ❤️ by Eng. Mohamed Shaban**

## ✨ Features

- 🤖 **AI-Powered**: Groq/OpenAI/Azure/Anthropic support
- 👥 **Multi-Tenant**: Isolated data per tenant
- 📱 **Multi-Channel**: Telegram, WhatsApp, Meta integrations
- ⚡ **Quick Replies**: Pre-defined button responses
- 📋 **Smart Rules**: Keyword-triggered instant answers
- 💬 **Chat Logs**: Full conversation history
- 👤 **Lead Capture**: Automatic customer lead extraction
- 🎨 **Modern UI**: HTMX + Tailwind dashboard
- 🚀 **Easy Deploy**: Single service on Render

## 🎯 Quick Start (Local)

### 1. Prerequisites
- Python 3.11+
- PostgreSQL database
- Virtual environment

### 2. Installation
```bash
# Clone and navigate to repo
cd ROBOVAI-BOT

# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration
Copy `.env.example` to `.env` and configure:
```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/robovai
SECRET_KEY=your-secret-key-here
ADMIN_PASSWORD=your-admin-password
GROQ_API_KEY=your-groq-api-key
LLM_MODEL=llama-3.1-70b-versatile
CORS_ALLOW_ORIGINS=*
```

### 4. Database Setup
```bash
# Run migrations
alembic upgrade head
```

### 5. Start Platform
```bash
# Easy way (recommended)
python start.py

# Or manually
python -m uvicorn app.main:app --reload
```

### 6. Access Dashboard
- **Dashboard**: http://localhost:8000/ui
- **API Docs**: http://localhost:8000/docs
- **Health**: http://localhost:8000/health

## 📱 Dashboard Pages

| Page | Description |
|------|-------------|
| 👥 **Tenants** | Manage tenants and API keys (admin only) |
| 📱 **Channels** | Configure Telegram/WhatsApp/Meta integrations |
| ⚡ **Quick Replies** | Create quick reply buttons |
| 📋 **Rules** | Define keyword-triggered responses |
| 👤 **Leads** | View captured customer leads |
| 💬 **Chat Logs** | Browse conversation history |
| ⚙️ **Settings** | Configure system prompt and webhooks |

## 🚀 Deploy to Render

### Option 1: Automated (render.yaml)
1. Push code to GitHub
2. In Render: New → Blueprint → Connect repo
3. Add environment variables: `ADMIN_PASSWORD`, `GROQ_API_KEY`
4. Deploy! 🎉

### Option 2: Manual
See [docs/DEPLOY_RENDER.md](docs/DEPLOY_RENDER.md) for detailed steps.

## 📚 Documentation

- [HTMX Dashboard Guide](docs/HTMX_DASHBOARD_GUIDE.md) - Complete UI walkthrough
- [Render Deployment](docs/DEPLOY_RENDER.md) - Production deployment guide

## 🔧 Tech Stack

- **Backend**: FastAPI + SQLAlchemy (async)
- **Database**: PostgreSQL
- **Frontend**: HTMX + Tailwind CSS (no build)
- **AI**: Groq/OpenAI/Azure/Anthropic
- **Deployment**: Render (single service)

## 🤝 Contributing

Contributions welcome! Open issues or submit PRs.

## 📄 License

MIT License - see LICENSE file for details.
