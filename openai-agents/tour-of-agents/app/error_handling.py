from datetime import timedelta

import restate

from agents import Agent
from restate import RunOptions
from restate.ext.openai import (
    restate_context,
    DurableRunner,
    durable_function_tool,
)

from utils.models import WeatherPrompt, WeatherRequest, WeatherResponse
from utils.utils import fetch_weather


# <start_here>
@durable_function_tool
async def get_weather(city: WeatherRequest) -> WeatherResponse:
    """Get the current weather for a given city."""
    return await restate_context().run_typed("get weather", fetch_weather, req=city)


# <end_here>


agent = Agent(
    name="WeatherAgent",
    model="gpt-0", # invalid model to trigger error
    instructions="You are a helpful agent that provides weather updates.",
    tools=[get_weather],
)


agent_service = restate.Service("WeatherAgent")


@agent_service.handler()
async def run(_ctx: restate.Context, req: WeatherPrompt) -> str:
    # <start_handle>
    try:
        run_opts = RunOptions(
            max_attempts=3, initial_retry_interval=timedelta(seconds=2)
        )
        result = await DurableRunner.run(agent, req.message, run_options=run_opts)
    except restate.TerminalError as e:
        # Handle terminal errors gracefully
        return f"The agent couldn't complete the request: {e.message}"
    # <end_handle>

    return result.final_output


if __name__ == "__main__":
    import hypercorn
    import asyncio

    app = restate.app(services=[agent_service])
    conf = hypercorn.Config()
    conf.bind = ["0.0.0.0:9080"]
    asyncio.run(hypercorn.asyncio.serve(app, conf))
