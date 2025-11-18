import restate

from google.adk import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types

from app.utils.models import WeatherResponse, WeatherPrompt
from app.utils.utils import call_weather_api
from google.adk.tools.tool_context import ToolContext
from google.adk.agents.llm_agent import Agent

from middleware.restate_plugin import RestatePlugin
from middleware.restate_utils import restate_overrides

APP_NAME = "agents"

agent_service = restate.Service("WeatherAgent")


# TOOLS
async def get_weather(tool_context: ToolContext, city: str) -> WeatherResponse:
    """Get the current weather for a given city."""
    restate_context = tool_context.session.state["restate_context"]

    #  call tool wrapped as Restate durable step
    return await restate_context.run_typed("Get weather", call_weather_api, city=city)


# AGENT
agent = Agent(
    model="gemini-2.0-flash",
    name="weather_agent",
    description="Agent that provides weather updates for cities.",
    instruction="You are a helpful agent that provides weather updates. Use the get_weather tool to fetch current weather information.",
    tools=[get_weather],
)


# HANDLER
@agent_service.handler()
async def run(ctx: restate.ObjectContext, req: WeatherPrompt) -> str:
    session_id = str(ctx.uuid())

    session_service = InMemorySessionService()
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
