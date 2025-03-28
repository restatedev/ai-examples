import json

import restate
from pydantic import BaseModel
from typing import Any

from utils.agent_session import run, AgentInput

# CHAT SERVICE
chat_service = restate.VirtualObject("ChatService")


class ChatMessage(BaseModel):
    """
    A chat message object.

    Args:
        message (str): The message to send.
    """

    message: str


@chat_service.handler()
async def send_message(
    ctx: restate.ObjectContext, req: ChatMessage
) -> list[dict[str, Any]]:
    import my_agents  # to fix circular import

    chat_history = await ctx.get("chat_history") or []
    chat_history.append(req.message)
    ctx.set("chat_history", chat_history)

    result = await ctx.object_call(
        run,
        key=ctx.key(),
        arg=AgentInput(
            starting_agent=my_agents.intake_agent,
            agents=my_agents.agents,
            message=req.message,  # this is the input for the LLM call
        ),
    )

    chat_history = await ctx.get("chat_history") or []
    new_message = json.loads(result.messages[-1]["content"])["content"][-1]["text"]
    chat_history.append(new_message)
    ctx.set("chat_history", chat_history)
    return new_message


@chat_service.handler()
async def receive_message(ctx: restate.ObjectContext, req: ChatMessage):
    """
    Add a message to the chat history of this chat session.
    This can be used to let the bank send messages to the customer.

    Args:
        req (ChatMessage): The message to add to the chat history
    """
    chat_history = await ctx.get("chat_history") or []
    chat_history.append(req.message)
    ctx.set("chat_history", chat_history)


@chat_service.handler(kind="shared")
async def get_chat_history(ctx: restate.ObjectSharedContext) -> list[str]:
    return await ctx.get("chat_history") or []
