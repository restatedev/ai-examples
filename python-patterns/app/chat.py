import restate
from pydantic import BaseModel
from restate import RunOptions

from .util.litellm_call import llm_call

"""
Long-lived, Stateful Chat Sessions

Maintains conversation state across multiple requests using Restate's persistent memory.
Sessions survive failures and can be resumed at any time.
"""

chat = restate.VirtualObject("Chat")

# Example input text to analyze
# Ask as feedback to make it funnier, or more technical, etc.
example_prompt = "Write a poem about Durable Execution"


class Prompt(BaseModel):
    message: str = example_prompt


@chat.handler()
async def message(ctx: restate.ObjectContext, prompt: Prompt) -> str | None:
    """A long-lived stateful chat session that allows for ongoing conversation."""

    memory = await ctx.get("memory", type_hint=list[dict]) or []
    memory.append({"role": "user", "content": prompt.message})

    result = await ctx.run_typed(
        "LLM call",
        llm_call,
        RunOptions(max_attempts=3),
        messages=memory,
    )

    memory.append({"role": "user", "content": result.content})
    ctx.set("memory", memory)
    return result.content
