import restate
from pydantic_ai import Agent
from restate import VirtualObject, ObjectContext
from restate.ext.pydantic import RestateAgent

from app.utils.models import MessageSerde
from utils.models import ChatMessage

# <start_here>
agent = Agent(
    "openai:gpt-4o-mini",
    system_prompt="You are a helpful assistant.",
)
restate_agent = RestateAgent(agent)

chat = VirtualObject("Chat")


@chat.handler()
async def message(ctx: ObjectContext, req: ChatMessage) -> str:
    # Load message history from Restate's durable key-value store
    history = await ctx.get("messages", serde=MessageSerde())

    result = await restate_agent.run(req.message, message_history=history)

    # Store updated history back in Restate state
    ctx.set("messages", result.all_messages(), serde=MessageSerde())
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
