import restate
from pydantic import BaseModel
from restate import Context, RunOptions

from app.util.litellm_call import llm_call
from app.util.util import fetch_weather, WeatherRequest

manual_loop_agent = restate.Service("ParallelToolAgent")

get_weather = {
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Get the current weather in a given location",
    },
}


class MultiWeatherPrompt(BaseModel):
    message: str = "What is the weather like in New York,  San Francisco, and Boston?"


@manual_loop_agent.handler()
async def run(ctx: Context, prompt: MultiWeatherPrompt) -> str:
    """Main agent loop with tool calling"""
    messages = [{"role": "user", "content": prompt.message}]

    while True:
        # Call OpenAI with durable execution
        response = await ctx.run_typed(
            "llm-call",
            llm_call,
            RunOptions(max_attempts=3),
            messages=messages,
            tools=[get_weather],
        )

        assistant_message = response.choices[0].message
        messages.append(assistant_message)

        if not assistant_message.tool_calls:
            return assistant_message.content

        # start all parallel tool calls with retries and recovery
        tool_output_promises = []
        for tool_call in assistant_message.tool_calls:
            if tool_call.function.name == "get_weather":
                tool_promise = ctx.run_typed(
                    "Get weather",
                    fetch_weather,
                    req=WeatherRequest.model_validate_json(
                        tool_call.function.arguments
                    ),
                )
                tool_output_promises.append(
                    {"id": tool_call.id, "promise": tool_promise}
                )

        # wait for all tool calls to complete
        await restate.gather(*tool_output_promises)

        # gather the results and add to messages
        for tool_output_promise in tool_output_promises:
            tool_output = await tool_output_promise["promise"]
            # Add tool response to messages
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_output_promise["id"],
                    "content": tool_output,
                }
            )
