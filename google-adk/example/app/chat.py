import restate
from google.adk import Runner
from google.adk.apps import App
from google.adk.sessions import Session
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

# Enables retries and recovery for model calls and tool executions
app = App(name=APP_NAME, root_agent=agent, plugins=[RestatePlugin()])
session_service = RestateSessionService()

chat = restate.VirtualObject("Chat")


# HANDLER
@chat.handler()
async def message(ctx: restate.ObjectContext, req: ChatMessage) -> str:
    session_id = ctx.key()
    with restate_overrides(ctx):
        await session_service.create_session(
            app_name=APP_NAME, user_id=req.user_id, session_id=session_id
        )

        runner = Runner(app=app, session_service=session_service)
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
                if event.content.parts[0].text:
                    final_response = event.content.parts[0].text
        return final_response
