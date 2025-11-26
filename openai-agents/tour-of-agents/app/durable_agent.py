import restate

from agents import (
    Agent,
    RunConfig,
    RunContextWrapper,
    ModelSettings,
)
from restate import TerminalError

from app.utils.middleware import Runner, function_tool
from app.utils.models import WeatherPrompt
from app.utils.utils import fetch_weather

@function_tool
async def get_weather(city: str) -> str:
    """Get the current weather for a given city."""
    return (await fetch_weather(city)).model_dump_json()


weather_agent = Agent(
    name="WeatherAgent",
    instructions="You are a helpful agent that provides weather updates.",
    tools=[get_weather],
)

agent_service = restate.Service("WeatherAgent")

@agent_service.handler()
async def run(restate_context: restate.Context, prompt: WeatherPrompt) -> str:
    result = await Runner.run(weather_agent, input=prompt.message)
    return result.final_output
