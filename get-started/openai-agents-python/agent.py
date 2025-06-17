import restate

from agents import Agent, RunConfig, Runner, function_tool, RunContextWrapper
from pydantic import BaseModel

from utils.middleware import DurableModelCalls
from utils.utils import fetch_weather, parse_weather_data, WeatherResponse


class WeatherRequest(BaseModel):
    """Request to get the weather for a city."""
    city: str


@function_tool
async def get_weather(
    wrapper: RunContextWrapper[restate.Context], req: WeatherRequest
) -> WeatherResponse:
    """Get the current weather for a given city."""
    # Do durable steps using the Restate context
    restate_context = wrapper.context
    resp = await restate_context.run(
        "Get weather", fetch_weather, args=(req.city,))
    return await parse_weather_data(resp)


my_agent = Agent[restate.Context](
    name="Helpful Agent",
    handoff_description="A helpful agent.",
    instructions="You are a helpful agent.",
    tools=[get_weather],
)


# Agent keyed by conversation id
agent = restate.Service("Agent")


@agent.handler()
async def run(restate_context: restate.Context, message: str) -> str:

    result = await Runner.run(
        my_agent,
        input=message,
        # Pass the Restate context to tools to make tool execution steps durable
        context=restate_context,
        # Choose any model and let Restate persist your calls
        run_config=RunConfig(
            model="gpt-4o",
            model_provider=DurableModelCalls(restate_context)
        ),
    )

    return result.final_output
