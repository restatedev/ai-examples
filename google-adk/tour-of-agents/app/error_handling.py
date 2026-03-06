import restate

from google.adk import Runner
from google.adk.apps import App
from google.genai.types import Content, Part
from google.adk.agents.llm_agent import Agent
from restate import TerminalError
from restate.ext.adk import RestatePlugin, restate_context, RestateSessionService

from utils.models import WeatherResponse, WeatherPrompt
from utils.utils import fetch_weather, parse_agent_response

APP_NAME = "agents"


async def get_weather(city: str) -> WeatherResponse:
    """Get the current weather for a given city."""
    #  Do one or more durable steps using the Restate context
    return await restate_context().run_typed(
        f"Get weather {city}", fetch_weather, city=city
    )


# Specify your agent in the default ADK way
agent = Agent(
    model="gemini-2.5-flash",
    name="weather_agent",
    instruction="You are a helpful agent that provides weather updates.",
    tools=[get_weather],
)

# <start_retries>
app = App(
    name=APP_NAME, root_agent=agent, plugins=[RestatePlugin(max_model_call_retries=3)]
)
# <end_retries>
runner = Runner(app=app, session_service=RestateSessionService())

agent_service = restate.VirtualObject("ErrorHandlingAgent")


# <start_handle>
@agent_service.handler()
async def run(ctx: restate.ObjectContext, req: WeatherPrompt) -> str | None:
    try:
        events = runner.run_async(
            user_id=req.user_id,
            session_id=req.session_id,
            new_message=Content(role="user", parts=[Part.from_text(text=req.message)]),
        )
        return await parse_agent_response(events)
    except TerminalError as e:
        # Handle the error appropriately, e.g., log it or return a default response
        print(f"An error occurred: {e}")
        return "Sorry, I'm unable to process your request at the moment."


# <end_handle>


if __name__ == "__main__":
    import hypercorn
    import asyncio

    restate_app = restate.app(services=[agent_service])
    conf = hypercorn.Config()
    conf.bind = ["0.0.0.0:9080"]
    asyncio.run(hypercorn.asyncio.serve(restate_app, conf))
