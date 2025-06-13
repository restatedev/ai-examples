import restate
import httpx

from agents import Agent, RunConfig, Runner, function_tool, RunContextWrapper
from pydantic import BaseModel, ConfigDict

from middleware import RestateModelProvider


# Pass the Restate context to the tools to journal tool execution steps
class ToolContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    restate_context: restate.Context
    # you can add more fields here to pass to your tools, e.g. customer_id, ...


@function_tool
async def get_weather(context: RunContextWrapper[ToolContext], city: str) -> str:
    """Get the current weather for a given city."""
    restate_ctx = context.context.restate_context

    async def get_weather_data(city: str) -> dict[str, str]:
        resp = httpx.get(f"https://wttr.in/{city}?format=j1", timeout=10.0)
        resp.raise_for_status()
        return resp.json()["current_condition"][0]

    data = await restate_ctx.run("Get weather", get_weather_data, args=(city,))
    return f"Weather in {city}: {data['temp_C']}°C, {data['weatherDesc'][0]['value']}"


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
