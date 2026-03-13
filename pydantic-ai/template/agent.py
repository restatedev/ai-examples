import restate
from pydantic import BaseModel
from pydantic_ai import Agent, RunContext
from restate.ext.pydantic import RestateAgent, restate_context


class WeatherPrompt(BaseModel):
    message: str = "What is the weather in San Francisco?"

# AGENT
weather_agent = Agent(
    "openai:gpt-4o-mini",
    system_prompt="You are a helpful agent that provides weather updates.",
)
restate_agent = RestateAgent(weather_agent)

@weather_agent.tool()
async def get_weather(_run_ctx: RunContext[None], city: str) -> dict:
    """Get the current weather for a given city."""

    # Do durable steps using the Restate context
    async def call_weather_api(city: str) -> dict:
        return {"temperature": 23, "description": "Sunny and warm."}

    return await restate_context().run_typed(
        f"Get weather {city}", call_weather_api, city=city
    )

# AGENT SERVICE
agent_service = restate.Service("agent")


@agent_service.handler()
async def run(_ctx: restate.Context, req: WeatherPrompt) -> str:
    result = await restate_agent.run(req.message)
    return result.output
