import restate

from google.adk import Runner
from google.adk.apps import App
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, Part
from google.adk.agents.llm_agent import Agent
from restate.ext.adk import RestatePlugin, restate_object_context

from app.utils.models import WeatherResponse, WeatherPrompt
from app.utils.utils import call_weather_api

APP_NAME = "agents"


# TOOLS
async def get_weather(city: str) -> WeatherResponse:
    """Get the current weather for a given city."""
    #  Do one or more durable steps using the Restate context
    return await restate_object_context().run_typed(
        f"Get weather {city}", call_weather_api, city=city
    )


# Specify your agent in the default ADK way
agent = Agent(
    model="gemini-2.5-flash",
    name="weather_agent",
    instruction="""You are a helpful agent that provides weather updates.
    Use the get_weather tool to fetch current weather information.""",
    tools=[get_weather],
)

app = App(name=APP_NAME, root_agent=agent, plugins=[RestatePlugin()])

agent_service = restate.Service("WeatherAgent")


@agent_service.handler()
async def run(_ctx: restate.Context, req: WeatherPrompt) -> str | None:
    session_service = InMemorySessionService()
    await session_service.create_session(
        app_name=APP_NAME, user_id="user-123", session_id=req.session_id
    )

    runner = Runner(app=app, session_service=session_service)
    events = runner.run_async(
        user_id="user-123",
        session_id=req.session_id,
        new_message=Content(role="user", parts=[Part.from_text(text=req.message)]),
    )

    final_response = None
    async for event in events:
        if event.is_final_response() and event.content and event.content.parts:
            if event.content.parts[0].text:
                final_response = event.content.parts[0].text
    return final_response
