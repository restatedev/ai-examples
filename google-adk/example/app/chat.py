import restate
from google.adk import Runner
from google.genai import types as genai_types

from app.utils.models import ChatMessage
from google.adk.agents.llm_agent import Agent

from middleware.restate_plugin import RestatePlugin
from middleware.restate_session_service import RestateSessionService
from middleware.restate_utils import restate_overrides

APP_NAME = "agents"

# AGENT
agent = Agent(
    model="gemini-2.5-flash",
    name="assistant",
    description="A helpful assistant that can answer questions.",
    instruction="You are a helpful assistant. Be concise and helpful.",
)

chat = restate.VirtualObject("Chat")


# HANDLER
@chat.handler()
async def message(ctx: restate.ObjectContext, req: ChatMessage) -> str:
    # Restate runner which uses RestateSessionService to persist session state in Restate
    session_id = ctx.key()
    session_service = RestateSessionService(ctx)
    await session_service.create_session(
        app_name=APP_NAME, user_id=req.user_id, session_id=session_id
    )

    runner = Runner(
        agent=agent,
        app_name=APP_NAME,
        session_service=session_service,
        # Enables retries and recovery for model calls and tool executions
        plugins=[RestatePlugin(ctx)],
    )
    with restate_overrides(ctx):
        events = runner.run_async(
            user_id=req.user_id,
            session_id=session_id,
            new_message=genai_types.Content(
                role="user", parts=[genai_types.Part.from_text(text=req.message)]
            ),
        )
        final_response = ""
        async for event in events:
            if event.is_final_response() and event.content and event.content.parts:
                final_response = event.content.parts[0].text

    return final_response


@chat.handler(kind="shared")
async def get_history(ctx: restate.ObjectSharedContext):
    return await ctx.get("items") or []
