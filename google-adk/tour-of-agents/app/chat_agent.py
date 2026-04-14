import restate
from google.adk import Runner
from google.adk.apps import App
from google.genai.types import Content, Part
from google.adk.agents.llm_agent import Agent
from restate.ext.adk import RestateSessionService, RestatePlugin
from utils.models import ChatMessage
from utils.utils import parse_agent_response

APP_NAME = "agents"

# <start_here>
agent = Agent(
    model="gemini-2.5-flash",
    name="assistant",
    instruction="You are a helpful assistant. Be concise and helpful.",
)
app = App(name=APP_NAME, root_agent=agent, plugins=[RestatePlugin()])
runner = Runner(app=app, session_service=RestateSessionService())

chat = restate.VirtualObject("Chat")


@chat.handler()
async def message(ctx: restate.ObjectContext, req: ChatMessage) -> str | None:
    events = runner.run_async(
        user_id=ctx.key(),
        session_id=req.session_id,
        new_message=Content(role="user", parts=[Part.from_text(text=req.message)]),
    )
    return await parse_agent_response(events)


@chat.handler(kind="shared")
async def get_history(ctx: restate.ObjectSharedContext, session_id: str):
    return await ctx.get(f"session_store::{session_id}", type_hint=list[dict]) or []


# <end_here>

if __name__ == "__main__":
    import hypercorn
    import asyncio

    restate_app = restate.app(services=[chat])
    conf = hypercorn.Config()
    conf.bind = ["0.0.0.0:9080"]
    asyncio.run(hypercorn.asyncio.serve(restate_app, conf))
