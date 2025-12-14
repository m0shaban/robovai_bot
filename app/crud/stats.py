from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat_log import ChatLog, SenderType
from app.models.lead import Lead
from app.models.tenant import Tenant
from app.models.channel_integration import ChannelIntegration


async def get_dashboard_stats(
    *,
    session: AsyncSession,
    tenant_id: int | None = None,
) -> dict[str, Any]:
    """Get comprehensive dashboard statistics"""
    
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)
    
    stats = {}
    
    # Base filters
    if tenant_id:
        lead_filter = Lead.tenant_id == tenant_id
    else:
        lead_filter = True
    
    # === Total Counts ===
    
    # Total leads (customers)
    total_leads = await session.execute(
        select(func.count(Lead.id)).where(lead_filter)
    )
    stats["total_leads"] = total_leads.scalar() or 0
    
    # Total messages
    if tenant_id:
        total_msgs = await session.execute(
            select(func.count(ChatLog.id))
            .join(Lead, Lead.id == ChatLog.lead_id)
            .where(Lead.tenant_id == tenant_id)
        )
    else:
        total_msgs = await session.execute(select(func.count(ChatLog.id)))
    stats["total_messages"] = total_msgs.scalar() or 0
    
    # Messages by type
    if tenant_id:
        user_msgs = await session.execute(
            select(func.count(ChatLog.id))
            .join(Lead, Lead.id == ChatLog.lead_id)
            .where(and_(Lead.tenant_id == tenant_id, ChatLog.sender_type == SenderType.user))
        )
        bot_msgs = await session.execute(
            select(func.count(ChatLog.id))
            .join(Lead, Lead.id == ChatLog.lead_id)
            .where(and_(Lead.tenant_id == tenant_id, ChatLog.sender_type == SenderType.bot))
        )
    else:
        user_msgs = await session.execute(
            select(func.count(ChatLog.id)).where(ChatLog.sender_type == SenderType.user)
        )
        bot_msgs = await session.execute(
            select(func.count(ChatLog.id)).where(ChatLog.sender_type == SenderType.bot)
        )
    
    stats["user_messages"] = user_msgs.scalar() or 0
    stats["bot_messages"] = bot_msgs.scalar() or 0
    
    # Response rate
    if stats["user_messages"] > 0:
        stats["response_rate"] = round((stats["bot_messages"] / stats["user_messages"]) * 100, 1)
    else:
        stats["response_rate"] = 0
    
    # === Today's Stats ===
    if tenant_id:
        today_leads = await session.execute(
            select(func.count(Lead.id))
            .where(and_(lead_filter, Lead.created_at >= today_start))
        )
        today_msgs = await session.execute(
            select(func.count(ChatLog.id))
            .join(Lead, Lead.id == ChatLog.lead_id)
            .where(and_(Lead.tenant_id == tenant_id, ChatLog.timestamp >= today_start))
        )
    else:
        today_leads = await session.execute(
            select(func.count(Lead.id)).where(Lead.created_at >= today_start)
        )
        today_msgs = await session.execute(
            select(func.count(ChatLog.id)).where(ChatLog.timestamp >= today_start)
        )
    
    stats["today_leads"] = today_leads.scalar() or 0
    stats["today_messages"] = today_msgs.scalar() or 0
    
    # === This Week Stats ===
    if tenant_id:
        week_leads = await session.execute(
            select(func.count(Lead.id))
            .where(and_(lead_filter, Lead.created_at >= week_ago))
        )
        week_msgs = await session.execute(
            select(func.count(ChatLog.id))
            .join(Lead, Lead.id == ChatLog.lead_id)
            .where(and_(Lead.tenant_id == tenant_id, ChatLog.timestamp >= week_ago))
        )
    else:
        week_leads = await session.execute(
            select(func.count(Lead.id)).where(Lead.created_at >= week_ago)
        )
        week_msgs = await session.execute(
            select(func.count(ChatLog.id)).where(ChatLog.timestamp >= week_ago)
        )
    
    stats["week_leads"] = week_leads.scalar() or 0
    stats["week_messages"] = week_msgs.scalar() or 0
    
    # === Tenants count (global only) ===
    if not tenant_id:
        total_tenants = await session.execute(select(func.count(Tenant.id)))
        stats["total_tenants"] = total_tenants.scalar() or 0
        
        # Active channels
        total_channels = await session.execute(select(func.count(ChannelIntegration.id)))
        stats["total_channels"] = total_channels.scalar() or 0
    
    return stats


async def get_messages_per_day(
    *,
    session: AsyncSession,
    tenant_id: int | None = None,
    days: int = 7,
) -> list[dict[str, Any]]:
    """Get message count per day for the last N days"""
    
    from sqlalchemy import cast, Date
    
    now = datetime.utcnow()
    start_date = now - timedelta(days=days)
    
    if tenant_id:
        stmt = (
            select(
                cast(ChatLog.timestamp, Date).label("date"),
                func.count(ChatLog.id).label("count")
            )
            .join(Lead, Lead.id == ChatLog.lead_id)
            .where(and_(Lead.tenant_id == tenant_id, ChatLog.timestamp >= start_date))
            .group_by(cast(ChatLog.timestamp, Date))
            .order_by(cast(ChatLog.timestamp, Date))
        )
    else:
        stmt = (
            select(
                cast(ChatLog.timestamp, Date).label("date"),
                func.count(ChatLog.id).label("count")
            )
            .where(ChatLog.timestamp >= start_date)
            .group_by(cast(ChatLog.timestamp, Date))
            .order_by(cast(ChatLog.timestamp, Date))
        )
    
    result = await session.execute(stmt)
    rows = result.all()
    
    # Fill in missing days with 0
    date_counts = {str(row.date): row.count for row in rows}
    chart_data = []
    for i in range(days):
        date = (now - timedelta(days=days - 1 - i)).date()
        chart_data.append({
            "date": str(date),
            "label": date.strftime("%m/%d"),
            "count": date_counts.get(str(date), 0)
        })
    
    return chart_data


async def get_recent_activity(
    *,
    session: AsyncSession,
    tenant_id: int | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Get recent chat activity"""
    
    if tenant_id:
        stmt = (
            select(ChatLog, Lead)
            .join(Lead, Lead.id == ChatLog.lead_id)
            .where(Lead.tenant_id == tenant_id)
            .order_by(ChatLog.timestamp.desc())
            .limit(limit)
        )
    else:
        stmt = (
            select(ChatLog, Lead)
            .join(Lead, Lead.id == ChatLog.lead_id)
            .order_by(ChatLog.timestamp.desc())
            .limit(limit)
        )
    
    result = await session.execute(stmt)
    rows = result.all()
    
    activity = []
    for chat_log, lead in rows:
        activity.append({
            "id": chat_log.id,
            "message": chat_log.message[:100] + "..." if len(chat_log.message) > 100 else chat_log.message,
            "sender_type": chat_log.sender_type.value,
            "timestamp": chat_log.timestamp,
            "customer_name": lead.customer_name or "مجهول",
            "lead_id": lead.id,
        })
    
    return activity
