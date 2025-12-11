import restate

from google.adk import Runner
from google.adk.apps import App
from google.genai.types import Content, Part
from google.adk.agents.llm_agent import Agent
from restate.ext.adk import RestateSessionService, RestatePlugin

from app.utils.models import ChatMessage

APP_NAME = "agents"

# AGENT
agent = Agent(
    model="gemini-2.5-flash",
    name="assistant",
    instruction="You are a helpful assistant. Be concise and helpful.",
)

# Enables retries and recovery for model calls and tool executions
app = App(name=APP_NAME, root_agent=agent, plugins=[RestatePlugin()])
runner = Runner(app=app, session_service=RestateSessionService())

chat = restate.VirtualObject("Chat")


# HANDLER
@chat.handler()
async def message(ctx: restate.ObjectContext, req: ChatMessage) -> str | None:
    events = runner.run_async(
        user_id=ctx.key(),
        session_id=req.session_id,
        new_message=Content(role="user", parts=[Part.from_text(text=req.message)]),
    )
    final_response = None
    async for event in events:
        if event.is_final_response() and event.content and event.content.parts:
            if event.content.parts[0].text:
                final_response = event.content.parts[0].text
    return final_response
