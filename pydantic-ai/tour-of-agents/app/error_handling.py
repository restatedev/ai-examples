import restate

from pydantic_ai import Agent
from restate import TerminalError, RunOptions
from restate.ext.pydantic import RestateAgent, restate_context
from datetime import timedelta

from utils.models import WeatherPrompt, WeatherRequest, WeatherResponse
from utils.utils import fetch_weather


# <start_here>
async def get_weather(city: WeatherRequest) -> WeatherResponse:
    """Get the current weather for a given city."""
    return await restate_context().run_typed(
        f"Get weather {city}", fetch_weather, req=city
    )


# <end_here>


agent = Agent(
    "openai:gpt-4o-mini",
    system_prompt="You are a helpful agent that provides weather updates.",
    tools=[get_weather],
)
# <start_retries>
restate_agent = RestateAgent(
    agent,
    run_options=RunOptions(max_attempts=3, initial_retry_interval=timedelta(seconds=2)),
)
# <end_retries>


agent_service = restate.Service("WeatherAgent")


# <start_handle>
@agent_service.handler()
async def run(_ctx: restate.Context, req: WeatherPrompt) -> str:
    try:
        result = await restate_agent.run(req.message)
    except TerminalError as e:
        # Handle terminal errors gracefully
        return f"The agent couldn't complete the request: {e.message}"
    return result.output


# <end_handle>


if __name__ == "__main__":
    import hypercorn
    import asyncio

    app = restate.app(services=[agent_service])
    conf = hypercorn.Config()
    conf.bind = ["0.0.0.0:9080"]
    asyncio.run(hypercorn.asyncio.serve(app, conf))
