"""
Broadcast execution service.
Handles sending broadcast messages to multiple channels.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.broadcast import get_broadcast, update_broadcast_stats
from app.crud.channel_integration import list_integrations_for_tenant
from app.crud.lead import list_leads
from app.models.broadcast import BroadcastStatus
from app.models.channel_integration import ChannelType
from app.services.telegram_service import send_telegram_message
from app.services.meta_service import send_whatsapp_text, send_page_message_text

logger = logging.getLogger(__name__)


async def execute_broadcast(
    session: AsyncSession,
    broadcast_id: int,
) -> dict[str, int]:
    """
    Execute a broadcast campaign.
    Returns stats: {sent: int, failed: int}
    """
    broadcast = await get_broadcast(session, broadcast_id)
    if not broadcast:
        logger.error(f"Broadcast {broadcast_id} not found")
        return {"sent": 0, "failed": 0}

    if broadcast.status != BroadcastStatus.DRAFT:
        logger.warning(f"Broadcast {broadcast_id} is not in DRAFT status")
        return {"sent": 0, "failed": 0}

    # Update status to SENDING
    broadcast.status = BroadcastStatus.SENDING
    broadcast.sent_at = datetime.utcnow()
    session.add(broadcast)
    await session.commit()

    # Get target audience
    leads = await list_leads(
        session=session,
        tenant_id=broadcast.tenant_id,
        page=1,
        page_size=10000,  # TODO: Implement pagination for large broadcasts
    )
    target_leads = leads[0]  # list_leads returns (leads, total)

    # Get active channels
    integrations = await list_integrations_for_tenant(
        session=session,
        tenant_id=broadcast.tenant_id,
        active_only=True,
    )

    if not integrations:
        logger.error(f"No active channels for tenant {broadcast.tenant_id}")
        broadcast.status = BroadcastStatus.FAILED
        await session.commit()
        return {"sent": 0, "failed": 0}

    sent_count = 0
    failed_count = 0

    # Send to each lead
    for lead in target_leads:
        if not lead.phone_number:
            continue

        # Try each channel until one succeeds
        message_sent = False

        for integ in integrations:
            try:
                if integ.channel_type == ChannelType.TELEGRAM and integ.access_token:
                    # For Telegram, we need chat_id which we might not have
                    # Skip for now or implement chat_id mapping
                    continue

                elif (
                    integ.channel_type == ChannelType.WHATSAPP
                    and integ.access_token
                    and integ.external_id
                ):
                    await send_whatsapp_text(
                        access_token=integ.access_token,
                        phone_number_id=integ.external_id,
                        to=lead.phone_number,
                        text=broadcast.message_content,
                    )
                    message_sent = True
                    break

                elif (
                    integ.channel_type in [ChannelType.MESSENGER, ChannelType.INSTAGRAM]
                    and integ.access_token
                ):
                    # For Messenger/IG, we need recipient_id
                    # Skip for now or implement recipient_id mapping
                    continue

            except Exception as e:
                logger.error(f"Failed to send via {integ.channel_type}: {e}")
                continue

        if message_sent:
            sent_count += 1
        else:
            failed_count += 1

    # Update broadcast stats
    broadcast.sent_count = sent_count
    broadcast.failed_count = failed_count
    broadcast.status = (
        BroadcastStatus.COMPLETED if failed_count == 0 else BroadcastStatus.FAILED
    )
    session.add(broadcast)
    await session.commit()

    logger.info(
        f"Broadcast {broadcast_id} completed: "
        f"{sent_count} sent, {failed_count} failed"
    )

    return {"sent": sent_count, "failed": failed_count}


async def schedule_broadcast(
    session: AsyncSession,
    broadcast_id: int,
    scheduled_at: datetime,
) -> bool:
    """
    Schedule a broadcast for future execution.
    TODO: Integrate with background job queue (Celery/Arq/APScheduler)
    """
    broadcast = await get_broadcast(session, broadcast_id)
    if not broadcast:
        return False

    broadcast.scheduled_at = scheduled_at
    broadcast.status = BroadcastStatus.SCHEDULED
    session.add(broadcast)
    await session.commit()

    logger.info(f"Broadcast {broadcast_id} scheduled for {scheduled_at}")

    # TODO: Add to job queue
    # job_queue.enqueue_at(scheduled_at, execute_broadcast, session, broadcast_id)

    return True
