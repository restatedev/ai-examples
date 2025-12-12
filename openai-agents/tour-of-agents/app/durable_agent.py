import restate

from agents import (
    Agent,
    RunConfig,
    RunContextWrapper,
    ModelSettings,
    Runner,
    function_tool,
)
from restate import Service
from restate.ext.openai.runner_wrapper import DurableOpenAIAgents, durable_function_tool

from app.utils.models import WeatherPrompt, WeatherRequest, WeatherResponse
from app.utils.utils import fetch_weather


@durable_function_tool
async def get_weather(city: WeatherRequest) -> WeatherResponse:
    """Get the current weather for a given city."""
    return await fetch_weather(city)


weather_agent = Agent(
    name="WeatherAgent",
    instructions="You are a helpful agent that provides weather updates.",
    tools=[get_weather],
)

agent_service = Service(
    "WeatherAgent", invocation_context_managers=[DurableOpenAIAgents]
)


@agent_service.handler()
async def run(restate_context: restate.Context, prompt: WeatherPrompt) -> str:
    result = await Runner.run(weather_agent, prompt.message)
    return result.final_output
