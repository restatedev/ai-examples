import restate

from agents import Agent, Runner
from restate.ext.openai import DurableOpenAIAgents
from restate.ext.openai.runner_wrapper import durable_function_tool

from app.utils.models import WeatherPrompt, WeatherRequest, WeatherResponse
from app.utils.utils import fetch_weather


# <start_here>
@durable_function_tool
async def get_weather(req: WeatherRequest) -> WeatherResponse:
    """Get the current weather for a given city."""
    return await fetch_weather(req.city)


# <end_here>


weather_agent = Agent(
    name="WeatherAgent",
    instructions="You are a helpful agent that provides weather updates.",
    tools=[get_weather],
)


agent_service = restate.Service(
    "WeatherAgent", invocation_context_managers=[DurableOpenAIAgents]
)


@agent_service.handler()
async def run(prompt: WeatherPrompt) -> str:
    # <start_handle>
    try:
        result = await Runner.run(weather_agent, input=prompt.message)
    except restate.TerminalError as e:
        # Handle terminal errors gracefully
        return "The agent couldn't complete the request."
    # <end_handle>

    return result.final_output
