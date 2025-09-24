import restate
from pydantic import BaseModel

from util import llm_call

chat = restate.VirtualObject("Chat")

# Example input text to analyze
# Ask as feedback to make it funnier, or more technical, etc.
example_prompt = "Write a poem about Durable Execution"


class Prompt(BaseModel):
    message: str = example_prompt


@chat.handler()
async def message(ctx: restate.ObjectContext, prompt: Prompt) -> str:
    """A long-lived stateful chat session that allows for ongoing conversation."""

    memory = await ctx.get("memory") or []

    result = await ctx.run_typed(
        "LLM call", llm_call, prompt=f"Task: {prompt} Previous messages {memory}"
    )

    memory.append(result)
    ctx.set("memory", memory)
    return result
