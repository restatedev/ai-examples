import restate

from google.adk import Runner
from google.adk.apps import App
from google.genai.types import Content, Part
from google.adk.tools.tool_context import ToolContext
from google.adk.agents.llm_agent import Agent
from restate.ext.adk import RestateSessionService, RestatePlugin

from app.utils.models import WeatherResponse, WeatherPrompt
from app.utils.utils import call_weather_api

APP_NAME = "agents"


# TOOLS
async def get_weather(tool_context: ToolContext, city: str) -> WeatherResponse:
    """Get the current weather for a given city."""
    restate_context = tool_context.session.state["restate_context"]

    #  call tool wrapped as Restate durable step
    return await restate_context.run_typed("Get weather", call_weather_api, city=city)


agent = Agent(
    model="gemini-2.5-flash",
    name="weather_agent",
    instruction="""You are a helpful agent that provides weather updates.
    Use the get_weather tool to fetch current weather information.""",
    tools=[get_weather],
)

app = App(name=APP_NAME, root_agent=agent, plugins=[RestatePlugin()])
session_service = RestateSessionService()


agent_service = restate.VirtualObject("StatefulWeatherAgent")


# HANDLER
@agent_service.handler()
async def run(ctx: restate.ObjectContext, req: WeatherPrompt) -> str | None:
    runner = Runner(app=app, session_service=session_service)
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
