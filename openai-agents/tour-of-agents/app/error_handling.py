import restate

from agents import Agent, RunConfig, Runner, function_tool, RunContextWrapper, ModelSettings

from app.utils.middleware import DurableModelCalls, raise_terminal_error
from app.utils.utils import (
    fetch_weather,
    WeatherRequest,
    WeatherResponse,
)


# <start_here>
@function_tool(failure_error_function=raise_terminal_error)
async def get_weather(
    wrapper: RunContextWrapper[restate.Context], req: WeatherRequest
) -> WeatherResponse:
    """Get the current weather for a given city."""
    restate_context = wrapper.context
    return await restate_context.run_typed("Get weather", fetch_weather, city=req.city)
# <end_here>


weather_agent = Agent[restate.Context](
    name="WeatherAgent",
    instructions="You are a helpful agent that provides weather updates.",
    tools=[get_weather],
)


agent_service = restate.Service("WeatherAgent")


@agent_service.handler()
async def run(restate_context: restate.Context, message: str) -> str:
    # <start_handle>
    try:
        result = await Runner.run(
            weather_agent,
            input=message,
            # Pass the Restate context to tools to make tool execution steps durable
            context=restate_context,
            # Choose any model and let Restate persist your calls
            run_config=RunConfig(
                model="gpt-4o",
                model_provider=DurableModelCalls(restate_context, max_retries=3),
                model_settings=ModelSettings(parallel_tool_calls=False)
            ),
        )
    except restate.TerminalError as e:
        # Handle terminal errors gracefully
        return "The agent couldn't complete the request."
    # <end_handle>

    return result.final_output
