"""
Parallel Tool Execution

Execute multiple tools in parallel with durable results that persist across failures.
"""

import restate
from pydantic import BaseModel
from restate import Context, RunOptions

from app.util.litellm_call import llm_call
from app.util.util import get_weather, WeatherRequest, tool, tool_result


class WeatherPrompt(BaseModel):
    message: str = "What is the weather in New York,  San Francisco, and Boston?"


parallel_tools_agent = restate.Service("ParallelToolAgent")


@parallel_tools_agent.handler()
async def run(ctx: Context, prompt: WeatherPrompt) -> str | None:
    """Main agent loop with tool calling"""
    messages = [{"role": "user", "content": prompt.message}]

    while True:
        # Call LLM with durable execution
        response = await ctx.run_typed(
            "llm-call",
            llm_call,
            RunOptions(max_attempts=3),
            messages=messages,
            tools=[
                tool(
                    name="get_weather",
                    description="Get the current weather for a location",
                    parameters=WeatherRequest.model_json_schema(),
                )
            ],
        )
        messages.append(response.dict())

        if not response.tool_calls:
            return response.content

        # Run all tool calls in parallel
        tool_promises = {
            tool_call.id: ctx.run_typed(
                "Get weather",
                get_weather,
                req=WeatherRequest.model_validate_json(tool_call.function.arguments),
            )
            for tool_call in response.tool_calls
            if tool_call.function.name == "get_weather"
        }

        #  Wait for all tools to complete and append results
        await restate.gather(*tool_promises.values())
        for tool_id, promise in tool_promises.items():
            output = await promise
            messages.append(tool_result(tool_id, "get_weather", output))
