import restate
from agents import Agent
from restate.ext.openai import restate_context, DurableRunner, durable_function_tool

@durable_function_tool
async def get_weather(city: str):
    """Get the current weather for a given city."""
    async def fetch_weather():
        return { "temp": 25, "condition": "sunny"}
    # Do durable steps using the Restate context
    return await restate_context().run_typed(
        "Get weather", fetch_weather, city=req.city
    )


weather_agent = Agent(
    name="WeatherAgent",
    instructions="You are a helpful agent that provides weather updates.",
    tools=[get_weather],
)


agent_service = restate.Service("agent")

@agent_service.handler()
async def run(_ctx: restate.Context, req: str) -> str:
    # Runner that persists the agent execution for recoverability
    result = await DurableRunner.run(weather_agent, req)
    return result.final_output
