# RoboVAI HTMX Dashboard - User Guide

## Overview

The new admin dashboard is built with FastAPI + HTMX + Tailwind CSS, providing a modern, responsive interface without requiring separate frontend build tools.

## Accessing the Dashboard

- **Local**: `http://localhost:8000/ui`
- **Production**: `https://<your-backend>.onrender.com/ui`

The dashboard automatically redirects to `/ui/tenants`.

## Pages & Features

### 1. 👥 Tenants

**Admin-only** (requires `ADMIN_PASSWORD` if set)

- View all tenants with their API keys, system prompts, and webhook URLs
- Create new tenants with optional system prompt and webhook
- Rotate API keys
- Update tenant names
- Delete tenants
- **Security**: API keys are displayed for easy integration, but ensure `ADMIN_PASSWORD` is set in production

### 2. 📱 Channels

Manage channel integrations (Telegram, Meta/WhatsApp, etc.)

- **Authentication**: Enter tenant API key to load channels
- View all channel integrations with verify tokens
- Add new channels with:
  - Channel type (telegram, meta, whatsapp)
  - External ID (bot ID, page ID)
  - Access token (optional)
  - Auto-generated verify token
- Delete channels
- **Use case**: Each channel integration receives webhooks from the respective platform

### 3. ⚡ Quick Replies

Create predefined quick reply buttons for chat interfaces

- **Authentication**: Tenant API key required
- Add quick replies with:
  - Title (button text shown to user)
  - Payload text (message sent when clicked)
  - Sort order (display order)
  - Active status
- Delete quick replies
- **Use case**: Common responses like "Talk to agent", "Business hours", etc.

### 4. 📋 Rules (Scripted Responses)

Define keyword-triggered automated responses

- **Authentication**: Tenant API key required
- Create rules with:
  - Trigger keyword (e.g., "pricing", "hours")
  - Response text (bot reply when keyword is detected)
  - Active status
- Delete rules
- **Use case**: Instant answers to common questions before AI engagement

### 5. 👤 Leads

View customer leads collected through conversations

- **Authentication**: Tenant API key required
- Display lead information:
  - Customer name
  - Phone number
  - Summary (extracted from conversation)
  - Creation timestamp
- **Read-only**: Leads are created automatically by the chat service

### 6. 💬 Chat Logs

Browse conversation history

- **Authentication**: Tenant API key required
- View recent chat messages with:
  - Lead ID (links to customer)
  - Sender type (Customer/Bot)
  - Message content
  - Timestamp
- **Read-only**: Logs are created automatically during chats
- **Limit**: Shows last 200 messages per tenant

### 7. ⚙️ Settings

Configure tenant-level settings

- **Authentication**: Tenant API key required
- Edit:
  - **System Prompt**: Instructions for AI assistant behavior
  - **Webhook URL**: Optional endpoint to receive lead/chat events
- Save changes with validation
- **Use case**: Customize AI personality and integrate with external CRM

## Technical Details

### Architecture

- **Backend**: FastAPI serves both API and HTML responses
- **Frontend**:
  - Tailwind CSS (CDN) for styling
  - HTMX for partial page updates without page reload
  - Jinja2 templates for server-side rendering
- **Deployment**: Single service on Render (no separate frontend)

### Authentication Model

- **Admin operations** (Tenants CRUD): Requires `ADMIN_PASSWORD` environment variable
- **Tenant operations** (all other pages): Requires tenant API key (obtained from Tenants page)
- **Security note**: In production, always set `ADMIN_PASSWORD` and use HTTPS

### HTMX Pattern

Most pages follow this pattern:

1. User enters tenant API key in sidebar/form
2. JavaScript calls HTMX to load data (`GET /ui/<resource>/rows?tenant_api_key=...`)
3. Server returns HTML partial (table rows)
4. HTML is swapped into `#<resource>-rows` div
5. Create/Delete operations similarly swap updated content without full page reload

### Styling

- **Dark theme**: Slate-900 background with subtle gradients
- **Responsive**: Works on mobile/tablet/desktop
- **Components**: Cards, tables, forms, buttons use consistent Tailwind classes
- **No build step**: Tailwind is loaded via CDN for simplicity

## Deployment Checklist

- [ ] Set `ADMIN_PASSWORD` environment variable
- [ ] Set `DATABASE_URL` to Postgres connection string
- [ ] Set `SECRET_KEY` to strong random value
- [ ] Configure `CORS_ALLOW_ORIGINS` if embedding widget
- [ ] Set LLM credentials: `LLM_BASE_URL`, `LLM_API_KEY`/`GROQ_API_KEY`, `LLM_MODEL`
- [ ] Run migrations: `alembic upgrade head`
- [ ] Test admin access at `/ui/tenants`
- [ ] Create first tenant and copy API key
- [ ] Test other pages with tenant API key

## Future Enhancements

- [ ] Edit rules/quick replies inline
- [ ] Export leads to CSV
- [ ] Real-time chat log streaming
- [ ] Bulk operations (delete multiple items)
- [ ] Toast notifications for success/error messages
- [ ] Copy-to-clipboard buttons for API keys and tokens
- [ ] Pagination for large datasets
- [ ] Search/filter functionality
