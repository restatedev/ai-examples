from datetime import timedelta

import restate

from agents import Agent, RunContextWrapper, function_tool
from restate import Context

from app.utils.middleware import RestateRunner, restate_function_tool
from app.utils.models import WeatherPrompt, WeatherRequest, WeatherResponse
from app.utils.utils import fetch_weather


@function_tool
async def get_weather(
    wrapper: RunContextWrapper[restate.Context], req: WeatherRequest
) -> WeatherResponse:
    """Get the current weather for a given city."""
    # Do durable steps using the Restate context
    restate_context = wrapper.context
    return await restate_context.run_typed("Get weather", fetch_weather, city=req.city)


weather_agent = Agent[restate.Context](
    name="WeatherAgent",
    instructions="You are a helpful agent that provides weather updates.",
    tools=[get_weather],
)

agent_service = restate.Service("WeatherAgent")


@agent_service.handler()
async def run(restate_context: Context, prompt: WeatherPrompt) -> str:
    result = await RestateRunner.run(
        restate_context=restate_context,
        starting_agent=weather_agent,
        input=prompt.message,
        context=restate_context,
    )
    return result.final_output
