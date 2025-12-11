import restate

from agents import Agent
from pydantic import BaseModel

from utils.context_utils import restate_overrides
from utils.middleware import Runner, function_tool
from utils.utils import fetch_weather, parse_weather_data, WeatherResponse


class WeatherRequest(BaseModel):
    """Request to get the weather for a city."""
    city: str


@function_tool
async def get_weather(req: WeatherRequest) -> WeatherResponse:
    """Get the current weather for a given city."""
    # Do durable steps using the Restate context
    resp = await fetch_weather(req.city)
    return await parse_weather_data(resp)


my_agent = Agent[restate.Context](
    name="Helpful Agent",
    model="gpt-4o",
    instructions="You are a helpful agent.",
    tools=[get_weather],
)


# Agent keyed by conversation id
agent = restate.Service("Agent")

@agent.handler()
async def run(restate_context: restate.Context, message: str) -> str:
    # Your LLM operations as spans under this trace
    with restate_overrides(ctx=restate_context):
        result = await Runner.run(my_agent, input=message)
        return result.final_output

