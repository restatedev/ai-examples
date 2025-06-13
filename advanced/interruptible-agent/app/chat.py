import os
import restate
import logging

from typing import Literal

from agent import run as agent_session_run, incorporate_new_input
from utils.models import ChatMessage, ChatHistory, AgentResponse, AgentInput

logger = logging.getLogger(__name__)

# Keyed by conversation ID
chat_service = restate.VirtualObject("ChatService")

# Keys of the K/V state stored in Restate per chat
CHAT_HISTORY = "chat_history"
ACTIVE_AGENT_INVOCATION_ID = "active_agent_inv_id"

# Sets the behavior of the agent when a new message is received and there is an ongoing agent run.
MODES = Literal["INTERRUPT", "INCORPORATE", "QUEUE"]


@chat_service.handler()
async def process_user_message(ctx: restate.ObjectContext, req: ChatMessage):
    """
    Send a message from the customer to the ChatService.
    This will be used as input to start an agent session.

    Args:
        req (ChatMessage): The message to send to the ChatService.
    """

    history = await ctx.get(CHAT_HISTORY, type_hint=ChatHistory) or ChatHistory()
    history.entries.append(req)
    ctx.set(CHAT_HISTORY, history)

    match os.getenv("MODE", "INTERRUPT").upper():
        case "INTERRUPT":
            ongoing_agent_run = await ctx.get(ACTIVE_AGENT_INVOCATION_ID)
            if ongoing_agent_run is not None:
                logger.info("Interrupting ongoing agent run")
                ctx.cancel_invocation(ongoing_agent_run)

            # Reinvoke with the new message
            await send_message_to_agent(ctx, history)
        case "INCORPORATE":
            # If there is an ongoing agent run, we need to incorporate the new message
            ongoing_agent_run = await ctx.get(ACTIVE_AGENT_INVOCATION_ID)
            if ongoing_agent_run is not None:
                logger.info("Incorporating new input into ongoing agent run")
                success = await ctx.object_call(
                    incorporate_new_input,
                    key=ctx.key(),
                    arg=req.content,
                )
                if success:
                    # If the new input was incorporated, we can return
                    return
            # (Fall back to) queue the new agent run
            await send_message_to_agent(ctx, history)
        case "QUEUE":
            # Queue the new agent run
            await send_message_to_agent(ctx, history)


async def send_message_to_agent(ctx, history):
    handle = ctx.object_send(
        agent_session_run,
        key=ctx.key(),
        arg=AgentInput(message_history=[entry.content for entry in history.entries]),
    )
    ctx.set(ACTIVE_AGENT_INVOCATION_ID, await handle.invocation_id())


@chat_service.handler()
async def process_agent_response(ctx: restate.ObjectContext, req: AgentResponse):
    """
    Receive an async response from the Agent.

    Args:
        req (ChatMessage): The message to send to add to the chat history.
    """
    new_message = ChatMessage(role="system", content=req.final_output)
    history = await ctx.get(CHAT_HISTORY, type_hint=ChatHistory) or ChatHistory()
    history.entries.append(new_message)
    ctx.set(CHAT_HISTORY, history)

    ctx.clear(ACTIVE_AGENT_INVOCATION_ID)
