import restate

from agents import Agent
from pydantic import BaseModel
from restate.ext.openai import restate_context, DurableRunner, durable_function_tool

class WeatherPrompt(BaseModel):
    message: str = "What is the weather in San Francisco?"

# TOOL
@durable_function_tool
async def get_weather(city: str) -> dict:
    """Get the current weather for a given city."""

    # Do durable steps using the Restate context
    async def call_weather_api(city: str) -> dict:
        return {"temperature": 23, "description": "Sunny and warm."}

    return await restate_context().run_typed(
        f"Get weather {city}", call_weather_api, city=city
    )


# AGENT
weather_agent = Agent(
    name="WeatherAgent",
    instructions="You are a helpful agent that provides weather updates.",
    tools=[get_weather],
)


# AGENT SERVICE
agent_service = restate.Service("agent")


@agent_service.handler()
async def run(_ctx: restate.Context, req: WeatherPrompt) -> str:
    # Runner that persists the agent execution for recoverability
    result = await DurableRunner.run(weather_agent, req.message)
    return result.final_output
