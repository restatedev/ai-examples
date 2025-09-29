from agents import Agent, RunConfig, Runner, ModelSettings
from restate import VirtualObject, ObjectContext, ObjectSharedContext

from app.utils.middleware import DurableModelCalls, RestateSession

chat = VirtualObject("Chat")

@chat.handler()
async def message(restate_context: ObjectContext, message: str) -> dict:
    result = await Runner.run(
        Agent("Assistant", "You are a helpful assistant."),
        input=message,
        run_config=RunConfig(
            model="gpt-4o",
            model_provider=DurableModelCalls(restate_context),
            model_settings=ModelSettings(parallel_tool_calls=False)
        ),
        session=RestateSession(session_id=restate_context.key(), ctx=restate_context)
    )
    return result.final_output

@chat.handler(kind="shared")
async def get_history(ctx: ObjectSharedContext):
    return await ctx.get("items") or []