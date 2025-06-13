import restate

from agents import Agent, RunConfig, Runner, function_tool, RunContextWrapper
from pydantic import BaseModel, ConfigDict

from utils.middleware import RestateModelProvider
from utils.utils import fetch_weather, parse_weather_data


# Pass the Restate context to the tools to journal tool execution steps
class ToolContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    restate_context: restate.Context
    # you can add more fields here to pass to your tools, e.g. customer_id, ...


class WeatherRequest(BaseModel):
    """Request to get the weather for a city."""

    city: str

    class Config:
        extra = "forbid"


@function_tool
async def get_weather(
    context: RunContextWrapper[ToolContext], req: WeatherRequest
) -> str:
    """Get the current weather for a given city."""
    # Do durable steps using the Restate context
    restate_ctx = context.context.restate_context

    response = await restate_ctx.run("Get weather", fetch_weather, args=(req.city,))
    if response.startswith("Unknown location"):
        return f"Unknown location: {req.city}. Please provide a valid city name."

    weather = await parse_weather_data(response)

    return (
        f"Weather in {req.city}: {weather["temperature"]}°C, {weather['description']}"
    )


my_agent = Agent[ToolContext](
    name="Helpful Agent",
    handoff_description="A helpful agent.",
    instructions="You are a helpful agent.",
    tools=[get_weather],
)


# Agent keyed by conversation id
agent = restate.Service("Agent")


@agent.handler()
async def run(ctx: restate.Context, message: str) -> str:

    result = await Runner.run(
        my_agent,
        input=message,
        # Pass the Restate context to tools to make tool execution steps durable
        context=ToolContext(restate_context=ctx),
        # Use the RestateModelProvider to persist the LLM calls in Restate
        run_config=RunConfig(model_provider=RestateModelProvider(ctx)),
    )
    return result.final_output
