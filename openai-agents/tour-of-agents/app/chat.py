import restate
from agents import Agent, RunConfig, Runner
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX
from restate import VirtualObject, ObjectContext, ObjectSharedContext

from app.utils.middleware import DurableModelCalls

chat_agent = Agent[restate.ObjectContext](
    name="Triage Agent",
    handoff_description="A triage agent that can delegate a customer's request to the appropriate agent.",
    instructions=(
        f"{RECOMMENDED_PROMPT_PREFIX} "
        "You are a helpful triaging agent. You can use your tools to delegate questions to other appropriate agents."
    )
)

chat = VirtualObject("Chat")

@chat.handler()
async def message(restate_context: ObjectContext, req: dict) -> dict:

    messages = await restate_context.get("messages") or []
    messages.append({"role": "user", "content": req["message"]})

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