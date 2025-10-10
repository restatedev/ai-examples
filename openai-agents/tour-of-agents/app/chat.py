from agents import Agent, RunConfig, Runner, ModelSettings
from restate import VirtualObject, ObjectContext, ObjectSharedContext

from app.utils.middleware import DurableModelCalls, RestateSession
from app.utils.models import ChatMessage

chat = VirtualObject("Chat")


@chat.handler()
async def message(restate_context: ObjectContext, chat_message: ChatMessage) -> dict:

    restate_session = await RestateSession.create(
        session_id=restate_context.key(), ctx=restate_context
    )

    result = await Runner.run(
        Agent(name="Assistant", instructions="You are a helpful assistant."),
        input=chat_message.message,
        run_config=RunConfig(
            model="gpt-4o",
            model_provider=DurableModelCalls(restate_context),
            model_settings=ModelSettings(parallel_tool_calls=False),
        ),
        session=restate_session,
    )
    return result.final_output


@chat.handler(kind="shared")
async def get_history(ctx: ObjectSharedContext):
    return await ctx.get("items") or []
