import restate

from agents import Agent, RunConfig, Runner, function_tool, RunContextWrapper

from utils.middleware import DurableModelCalls
from utils.utils import (
    fetch_weather,
    WeatherRequest,
    WeatherResponse,
)


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


agent_service = restate.Service("agent")


@agent_service.handler()
async def run(restate_context: restate.Context, message: str) -> str:

    result = await Runner.run(
        weather_agent,
        input=message,
        # Pass the Restate context to tools to make tool execution steps durable
        context=restate_context,
        # Choose any model and let Restate persist your calls
        run_config=RunConfig(
            model="gpt-4o", model_provider=DurableModelCalls(restate_context)
        ),
    )

    return result.final_output
