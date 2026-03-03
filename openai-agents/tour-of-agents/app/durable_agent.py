import restate

from datetime import timedelta
from agents import (
    Agent,
    RunConfig,
    RunContextWrapper,
    ModelSettings,
)
from restate import Service, VirtualObject
from restate.ext.openai import restate_context, DurableRunner, durable_function_tool

from app.utils.models import WeatherPrompt, WeatherRequest, WeatherResponse
from app.utils.utils import fetch_weather


@durable_function_tool
async def get_weather(city: WeatherRequest) -> WeatherResponse:
    """Get the current weather for a given city."""
    return await restate_context().run_typed("get weather", fetch_weather, req=city)


agent = Agent(
    name="WeatherAgent",
    instructions="You are a helpful agent that provides weather updates.",
    tools=[get_weather],
)

agent_service = restate.Service("WeatherAgent")


@agent_service.handler()
async def run(_ctx: restate.Context, req: WeatherPrompt) -> str:
    result = await DurableRunner.run(agent, req.message)
    return result.final_output


if __name__ == "__main__":
    import hypercorn
    import asyncio

    app = restate.app(services=[agent_service])
    conf = hypercorn.Config()
    conf.bind = ["0.0.0.0:9080"]
    asyncio.run(hypercorn.asyncio.serve(app, conf))
