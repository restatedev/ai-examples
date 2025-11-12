"""
Long-lived, Stateful Chat Sessions

Maintains conversation state across multiple requests using Restate's persistent memory.
Sessions survive failures and can be resumed at any time.
"""

import restate
from pydantic import BaseModel
from restate import RunOptions

from .util.litellm_call import llm_call


# Example input text to analyze
# Ask as feedback to make it funnier, or more technical, etc.
class ChatMessage(BaseModel):
    text: str = "Write a poem about Durable Execution"


chat = restate.VirtualObject("Chat")


@chat.handler()
async def on_message(ctx: restate.ObjectContext, message: ChatMessage) -> str | None:
    """A long-lived stateful chat session that allows for ongoing conversation."""

    # Retrieve conversation memory from Restate
    memory = await ctx.get("memory", type_hint=list[dict]) or []
    memory.append({"role": "user", "content": message.text})

    result = await ctx.run_typed(
        "LLM call",
        llm_call,
        RunOptions(max_attempts=3),
        messages=memory,
    )

    # Update conversation memory in Restate
    memory.append({"role": "assistant", "content": result.content})
    ctx.set("memory", memory)

    return result.content
