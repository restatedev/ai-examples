import restate
from agents import Agent, RunConfig, Runner
from restate import VirtualObject, ObjectContext, ObjectSharedContext

from app.utils.middleware import DurableModelCalls

chat_agent = Agent[restate.ObjectContext](
    name="Assistant",
    instructions="You are a helpful assistant."
)

chat = VirtualObject("Chat")

@chat.handler()
async def message(restate_context: ObjectContext, message: str) -> dict:

    messages = await restate_context.get("messages") or []
    messages.append({"role": "user", "content": message})

    result = await Runner.run(
        chat_agent,
        input=messages,
        # Pass the Restate context to the tools to make tool execution steps durable
        context=restate_context,
        # Choose any model and let Restate persist your calls
        run_config=RunConfig(model="gpt-4o", model_provider=DurableModelCalls(restate_context)),
    )

    messages.append({"role": "assistant", "content": result.final_output})
    restate_context.set("messages", messages)

    return result.final_output

@chat.handler(kind="shared")
async def get_history(ctx: ObjectSharedContext):
    return await ctx.get("messages") or []