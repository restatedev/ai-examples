import restate

from agents import Agent, RunConfig, Runner, function_tool, RunContextWrapper
from pydantic import BaseModel

from a2a.common.a2a.models import AgentInvokeResult, A2AAgent
from a2a.common.openai.middleware import DurableModelCalls, restate_tool_error_function
from utils import fetch_weather, parse_weather_data, WeatherResponse


class WeatherRequest(BaseModel):
    """Request to get the weather for a city."""

    city: str


@function_tool(failure_error_function=restate_tool_error_function)
async def get_weather(
    wrapper: RunContextWrapper[restate.ObjectContext], req: WeatherRequest
) -> WeatherResponse:
    """Get the current weather for a given city."""
    # Do durable steps using the Restate context
    restate_context = wrapper.context
    resp = await restate_context.run("Get weather", fetch_weather, args=(req.city,))

    return await parse_weather_data(resp)


weather_agent = Agent[restate.ObjectContext](
    name="WeatherAgent",
    handoff_description="Get the current weather for a city.",
    instructions="You are a helpful agent that uses the get_weather tool to find the weather for a city.",
    tools=[get_weather],
)


class WeatherAgent(A2AAgent):
    async def invoke(
        self, restate_context: restate.ObjectContext, query: str, session_id: str
    ) -> AgentInvokeResult:
        result = await Runner.run(
            weather_agent,
            input=query,
            # Pass the Restate context to tools to make tool execution steps durable
            context=restate_context,
            # Choose any model and let Restate persist your calls
            run_config=RunConfig(
                model="gpt-4o", model_provider=DurableModelCalls(restate_context)
            ),
        )
        result = result.final_output

        parts = [{"type": "text", "text": result}]
        requires_input = "MISSING_INFO:" in result
        completed = not requires_input
        return AgentInvokeResult(
            parts=parts,
            require_user_input=requires_input,
            is_task_complete=completed,
        )
