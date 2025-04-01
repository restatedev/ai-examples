import datetime
import json
from datetime import datetime

import restate
from pydantic import BaseModel
from typing import Any

from utils.agent_session import run, AgentInput

# MODELS

class ChatMessage(BaseModel):
    """
    A chat message object.

    Args:
        role (str): The role of the sender (user, assistant, system).
        content (str): The message to send.
        timestamp (int): The timestamp of the message in millis.
    """
    role: str
    content: str
    timestamp: int


class ChatHistory(BaseModel):
    """
    A chat history object.

    Args:
        entries (list[ChatMessage]): The list of chat messages.
    """
    entries: list[ChatMessage]


# CHAT SERVICE

# Keyed by customerID
chat_service = restate.VirtualObject("ChatService")

@chat_service.handler()
async def send_message(
    ctx: restate.ObjectContext, req: ChatMessage
) -> list[dict[str, Any]]:
    import my_agents  # to fix circular import

    chat_history = await ctx.get("chat_history", type_hint=ChatHistory) or ChatHistory(entries=[])
    chat_history.entries.append(req)
    ctx.set("chat_history", chat_history)

    result = await ctx.object_call(
        run,
        key=f"chat_{ctx.key()}",
        arg=AgentInput(
            starting_agent=my_agents.intake_agent,
            agents=my_agents.agents,
            message=f"For customer ID {ctx.key()}: {req.content}",  # this is the input for the LLM call
        ),
    )

    chat_history = await ctx.get("chat_history", type_hint=ChatHistory) or ChatHistory(entries=[])
    new_message = json.loads(result.messages[-1]["content"])["content"][-1]["text"]
    time_now = await ctx.run("time", lambda: round(datetime.now().timestamp() * 1000))
    chat_history.entries.append(ChatMessage(role="system", content=new_message, timestamp=time_now))
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
    chat_history = await ctx.get("chat_history", type_hint=ChatHistory) or ChatHistory(entries=[])
    chat_history.entries.append(req)
    ctx.set("chat_history", chat_history)


@chat_service.handler(kind="shared")
async def get_chat_history(ctx: restate.ObjectSharedContext) -> ChatHistory:
    return await ctx.get("chat_history", type_hint=ChatHistory) or ChatHistory(entries=[])
