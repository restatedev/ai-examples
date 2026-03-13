import restate
from pydantic_ai import Agent, ModelMessagesTypeAdapter
from pydantic_core import to_json
from restate import VirtualObject, ObjectContext
from restate.ext.pydantic import RestateAgent

from utils.models import ChatMessage

# <start_here>
assistant = Agent(
    "openai:gpt-4o-mini",
    system_prompt="You are a helpful assistant.",
)
restate_assistant = RestateAgent(assistant)

chat = VirtualObject("Chat")


@chat.handler()
async def message(ctx: ObjectContext, req: ChatMessage) -> str:
    # Load message history from Restate's durable key-value store
    messages_json = await ctx.get("messages", type_hint=dict)
    history = (
        ModelMessagesTypeAdapter.validate_python(messages_json)
        if messages_json
        else None
    )

    result = await restate_assistant.run(req.message, message_history=history)

    # Store updated history back in Restate state
    ctx.set("messages", to_json(result.all_messages()))
    return result.output


@chat.handler(kind="shared")
async def get_history(ctx: restate.ObjectSharedContext) -> dict:
    return await ctx.get("messages", type_hint=dict) or {}


# <end_here>


if __name__ == "__main__":
    import hypercorn
    import asyncio

    app = restate.app(services=[chat])
    conf = hypercorn.Config()
    conf.bind = ["0.0.0.0:9080"]
    asyncio.run(hypercorn.asyncio.serve(app, conf))
