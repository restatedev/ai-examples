import restate
from agents import Agent
from restate import VirtualObject, ObjectContext
from restate.ext.openai import DurableRunner

from utils.models import ChatMessage

# <start_here>
chat = VirtualObject("Chat")


@chat.handler()
async def message(_ctx: ObjectContext, req: ChatMessage) -> dict:
    # Set use_restate_session=True to store the session in Restate's key-value store
    # Make sure you use a VirtualObject to enable this feature
    result = await DurableRunner.run(
        Agent(name="Assistant", instructions="You are a helpful assistant."),
        req.message,
        use_restate_session=True,
    )
    return result.final_output


@chat.handler(kind="shared")
async def get_history(ctx: restate.ObjectSharedContext):
    return await ctx.get("messages", type_hint=list[dict]) or []
# <end_here>


if __name__ == "__main__":
    import hypercorn
    import asyncio

    app = restate.app(services=[chat])
    conf = hypercorn.Config()
    conf.bind = ["0.0.0.0:9080"]
    asyncio.run(hypercorn.asyncio.serve(app, conf))
