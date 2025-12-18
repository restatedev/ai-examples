import restate

from agents import Agent, function_tool
from restate.ext.openai import restate_context, DurableRunner

from utils.utils import (
    fetch_weather,
    WeatherRequest,
    WeatherResponse,
    WeatherPrompt,
)


@function_tool
async def get_weather(req: WeatherRequest) -> WeatherResponse:
    """Get the current weather for a given city."""
    # Do durable steps using the Restate context
    return await restate_context().run_typed(
        "Get weather", fetch_weather, city=req.city
    )


weather_agent = Agent(
    name="WeatherAgent",
    instructions="You are a helpful agent that provides weather updates.",
    tools=[get_weather],
)


agent_service = restate.Service("agent")


@agent_service.handler()
async def run(_ctx: restate.Context, req: WeatherPrompt) -> str:
    # Runner that persists the agent execution for recoverability
    result = await DurableRunner.run(weather_agent, req.message)
    return result.final_output
