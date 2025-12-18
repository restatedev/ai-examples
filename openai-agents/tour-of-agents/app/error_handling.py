from datetime import timedelta

import restate

from agents import Agent
from restate.ext.openai import (
    restate_context,
    DurableRunner,
    LlmRetryOpts,
    durable_function_tool,
)

from app.utils.models import WeatherPrompt, WeatherRequest, WeatherResponse
from app.utils.utils import fetch_weather


# <start_here>
@durable_function_tool
async def get_weather(city: WeatherRequest) -> WeatherResponse:
    """Get the current weather for a given city."""
    return await restate_context().run_typed("get weather", fetch_weather, req=city)


# <end_here>


agent = Agent(
    name="WeatherAgent",
    instructions="You are a helpful agent that provides weather updates.",
    tools=[get_weather],
)


agent_service = restate.Service("WeatherAgent")


@agent_service.handler()
async def run(_ctx: restate.Context, req: WeatherPrompt) -> str:
    # <start_handle>
    try:
        result = await DurableRunner.run(
            agent,
            req.message,
            llm_retry_opts=LlmRetryOpts(
                max_attempts=3, initial_retry_interval=timedelta(seconds=2)
            ),
        )
    except restate.TerminalError as e:
        # Handle terminal errors gracefully
        return f"The agent couldn't complete the request: {e.message}"
    # <end_handle>

    return result.final_output
