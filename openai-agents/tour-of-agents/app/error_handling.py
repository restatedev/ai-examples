import restate

from agents import (
    Agent,
    RunContextWrapper,
)

from app.utils.middleware import Runner, function_tool
from app.utils.models import WeatherPrompt, WeatherRequest, WeatherResponse
from app.utils.utils import fetch_weather


# <start_here>
@function_tool
async def get_weather(
    wrapper: RunContextWrapper[restate.Context], req: WeatherRequest
) -> WeatherResponse:
    """Get the current weather for a given city."""
    return await fetch_weather(req.city)


# <end_here>


weather_agent = Agent[restate.Context](
    name="WeatherAgent",
    instructions="You are a helpful agent that provides weather updates.",
    tools=[get_weather],
)


agent_service = restate.Service("WeatherAgent")


@agent_service.handler()
async def run(restate_context: restate.Context, prompt: WeatherPrompt) -> str:
    # <start_handle>
    try:
        result = await Runner.run(
            weather_agent, input=prompt.message, context=restate_context
        )
    except restate.TerminalError as e:
        # Handle terminal errors gracefully
        return "The agent couldn't complete the request."
    # <end_handle>

    return result.final_output
