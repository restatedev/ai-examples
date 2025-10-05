import restate
from litellm.types.utils import Message
from pydantic import BaseModel

from .util.litellm_call import llm_call

chat = restate.VirtualObject("Chat")

# Example input text to analyze
# Ask as feedback to make it funnier, or more technical, etc.
example_prompt = "Write a poem about Durable Execution"


class Prompt(BaseModel):
    message: str = example_prompt


@chat.handler()
async def message(ctx: restate.ObjectContext, prompt: Prompt) -> str:
    """A long-lived stateful chat session that allows for ongoing conversation."""

    memory = await ctx.get("memory", type_hint=list[dict]) or []
    memory.append({"role": "user", "content": prompt.message})

    result = await ctx.run_typed(
        "LLM call",
        llm_call,
        restate.RunOptions(max_attempts=3),
        messages=memory,
    )

    memory.append({"role": "user", "content": result.content})
    ctx.set("memory", memory)
    return result.content
