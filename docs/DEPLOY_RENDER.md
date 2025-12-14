# Render Deployment Guide (Single Service)

## Quick Deploy (Automated with render.yaml)

1. **Push code to GitHub**
2. **Connect to Render**: 
   - Go to https://render.com
   - Click "New" → "Blueprint"
   - Connect your GitHub repo
   - Render will detect `render.yaml` and create services automatically

3. **Manual Environment Variables** (add in Render dashboard after deploy):
   - `ADMIN_PASSWORD` = your-secure-admin-password
   - `GROQ_API_KEY` or `LLM_API_KEY` = your-groq-api-key

4. **Access your app**:
   - Dashboard: `https://<your-app>.onrender.com/ui`
   - API Docs: `https://<your-app>.onrender.com/docs`

## Manual Deployment Steps

### 1. Create PostgreSQL Database
- Service Type: PostgreSQL
- Plan: Free
- Database Name: `robovai`
- Region: Frankfurt (or closest to you)
- Copy the **Internal Database URL** (starts with `postgresql://`)

### 2. Create Web Service
- Service Type: Web Service
- Runtime: Python 3.11+
- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Health Check Path: `/health`

### 3. Environment Variables
Add these in the Render dashboard:

```env
DATABASE_URL=<internal-postgres-url>
SECRET_KEY=<generate-random-64-chars>
ADMIN_PASSWORD=<your-admin-password>
CORS_ALLOW_ORIGINS=*
LLM_BASE_URL=https://api.groq.com/openai/v1
GROQ_API_KEY=<your-groq-api-key>
LLM_MODEL=llama-3.1-70b-versatile
WEBHOOK_TIMEOUT=5.0
```

### 4. Post-Deploy (Run Once)
Open Shell in Render and run:
```bash
python -m alembic upgrade head
```

Or add as deploy hook in `render.yaml`.

## First-Time Setup

1. **Access Dashboard**: `https://<your-app>.onrender.com/ui`
2. **Go to Tenants page** (opens automatically)
3. **Create first tenant**:
   - Enter admin password
   - Set tenant name
   - Optional: Add system prompt
   - Click "Add Tenant"
4. **Copy API key** (click 📋 button)
5. **Configure other pages** using the API key

## Features

✅ **Single unified service** (Backend + HTMX Dashboard)
✅ **Auto-migrations** on deploy
✅ **Health checks** enabled
✅ **Free tier** supported
✅ **HTTPS** included
✅ **Auto-scaling** ready

## Troubleshooting

### Service won't start
- Check logs in Render dashboard
- Verify DATABASE_URL is set
- Ensure all required env vars are present

### Database connection errors
- Use **Internal Database URL** (not External)
- Format: `postgresql+asyncpg://...`

### Admin password issues
- Set ADMIN_PASSWORD in Render env vars
- Restart service after adding env vars

### Free tier sleep
- Free services sleep after 15 min inactivity
- First request after sleep takes ~30 seconds
- Upgrade to paid plan for 24/7 availability

## Cost Estimate

- **Free Tier**: $0/month
  - PostgreSQL: 256MB RAM, 1GB storage
  - Web Service: 512MB RAM, sleeps after inactivity
  
- **Starter**: ~$7/month
  - PostgreSQL: 1GB RAM, 10GB storage
  - Web Service: 512MB RAM, no sleep

## Monitoring

- **Health**: Check `/health` endpoint
- **Logs**: View in Render dashboard
- **Metrics**: CPU, Memory, Request count available

## Updates

To deploy updates:
1. Push code to GitHub
2. Render auto-deploys (if auto-deploy enabled)
3. Or manually deploy from Render dashboard
