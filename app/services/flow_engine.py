from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.flow import Flow
from app.models.lead import Lead
from app.crud.flow import get_flow


async def process_flow(
    session: AsyncSession, lead: Lead, user_message: str
) -> str | None:
    """
    Continues an active flow for a lead.
    Returns the bot response text, or None if flow is finished/broken.
    """
    if not lead.current_flow_id or not lead.current_step_id:
        return None

    flow = await get_flow(session, lead.current_flow_id)
    if not flow or not flow.is_active:
        # Flow deleted or inactive, clear state
        await clear_flow_state(session, lead)
        return None

    nodes = flow.flow_data.get("nodes", [])
    node_map = {n["id"]: n for n in nodes}
    current_node = node_map.get(lead.current_step_id)

    if not current_node:
        await clear_flow_state(session, lead)
        return None

    # We are at a "Question" node waiting for input
    # 1. Save the answer
    variable_name = current_node.get("variable")
    if variable_name:
        context = dict(lead.flow_context)  # Copy
        context[variable_name] = user_message
        lead.flow_context = context
        session.add(lead)
    
    # 2. Move to next node
    next_node_id = current_node.get("next")
    return await execute_flow_steps(session, lead, flow, next_node_id)


async def start_flow(
    session: AsyncSession, lead: Lead, flow: Flow
) -> str | None:
    """
    Starts a flow for a lead.
    """
    # Reset state
    lead.current_flow_id = flow.id
    lead.flow_context = {}
    session.add(lead)

    # Find start node (first node or id='start')
    nodes = flow.flow_data.get("nodes", [])
    if not nodes:
        return None
    
    start_node = next((n for n in nodes if n.get("id") == "start"), nodes[0])
    return await execute_flow_steps(session, lead, flow, start_node["id"])


async def execute_flow_steps(
    session: AsyncSession, lead: Lead, flow: Flow, start_node_id: str | None
) -> str | None:
    """
    Executes nodes starting from start_node_id until a Question node or End.
    Returns the accumulated text response.
    """
    if not start_node_id:
        await clear_flow_state(session, lead)
        return None

    nodes = flow.flow_data.get("nodes", [])
    node_map = {n["id"]: n for n in nodes}
    
    current_id = start_node_id
    responses = []

    while current_id:
        node = node_map.get(current_id)
        if not node:
            break

        # Format text with context variables
        text_template = node.get("content", "")
        try:
            text = text_template.format(**lead.flow_context)
        except KeyError:
            text = text_template # Fallback if var missing

        responses.append(text)

        if node.get("type") == "question":
            # Stop here, wait for user input
            lead.current_step_id = current_id
            session.add(lead)
            await session.commit()
            return "\n\n".join(responses)
        
        # Move to next
        current_id = node.get("next")

    # End of flow
    await clear_flow_state(session, lead)
    await session.commit()
    return "\n\n".join(responses)


async def clear_flow_state(session: AsyncSession, lead: Lead):
    lead.current_flow_id = None
    lead.current_step_id = None
    lead.flow_context = {}
    session.add(lead)
    await session.commit()
