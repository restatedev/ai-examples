from agents import Agent, RunConfig, Runner
from restate import VirtualObject, ObjectContext, ObjectSharedContext

from app.utils.middleware import DurableModelCalls, RestateSession

chat_agent = Agent(
    name="Assistant",
    instructions="You are a helpful assistant."
)

chat = VirtualObject("Chat")

@chat.handler()
async def message(restate_context: ObjectContext, message: str) -> dict:
    result = await Runner.run(
        chat_agent,
        input=message,
        run_config=RunConfig(model="gpt-4o", model_provider=DurableModelCalls(restate_context, max_retries=3)),
        session=RestateSession(session_id=restate_context.key(), ctx=restate_context)
    )
    return result.final_output

@chat.handler(kind="shared")
async def get_history(ctx: ObjectSharedContext):
    return await ctx.get("messages") or []