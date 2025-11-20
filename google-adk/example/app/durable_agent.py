import restate

from google.adk import Runner
from google.adk.apps import App
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, Part
from app.utils.models import WeatherResponse, WeatherPrompt
from app.utils.utils import call_weather_api
from google.adk.tools.tool_context import ToolContext
from google.adk.agents.llm_agent import Agent

from middleware.restate_plugin import RestatePlugin
from middleware.restate_utils import restate_overrides

APP_NAME = "agents"


# TOOLS
async def get_weather(tool_context: ToolContext, city: str) -> WeatherResponse:
    """Get the current weather for a given city."""
    restate_context = tool_context.session.state["restate_context"]
    #  Do one or more durable steps using the Restate context
    return await restate_context.run_typed(
        f"Get weather {city}", call_weather_api, city=city
    )


# Specify your agent in the default ADK way
agent = Agent(
    model="gemini-2.5-flash",
    name="weather_agent",
    description="Agent that provides weather updates for cities.",
    instruction="You are a helpful agent that provides weather updates. "
                "Use the get_weather tool to fetch current weather information.",
    tools=[get_weather],
)

agent_service = restate.Service("WeatherAgent")

@agent_service.handler()
async def run(ctx: restate.Context, req: WeatherPrompt) -> str:
    session_id = str(ctx.uuid())
    session_service = InMemorySessionService()
    await session_service.create_session(
        app_name=APP_NAME, user_id=req.user_id, session_id=session_id
    )

    # Use the Restate plugin to enable retries, recovery, and workflows
    app = App(name=APP_NAME, root_agent=agent, plugins=[RestatePlugin(ctx)])
    runner = Runner(app=app, session_service=session_service)

    with restate_overrides(ctx):
        events = runner.run_async(
            user_id=req.user_id,
            session_id=session_id,
            new_message=Content(role="user", parts=[Part.from_text(text=req.message)]),
        )
        final_response = ""
        async for event in events:
            if event.is_final_response() and event.content and event.content.parts:
                final_response = event.content.parts[0].text
    return final_response
