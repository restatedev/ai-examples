import litellm
import restate
from restate import Context

from app.util.util import get_weather, WeatherRequest

weather_agent = restate.Service("WeatherAgent")


@weather_agent.handler()
async def run(ctx: Context, prompt: str) -> str:
    """Main agent loop with tool calling"""
    messages = [{"role": "user", "content": prompt}]

    while True:
        # Call LLM with durable execution
        result = await ctx.run_typed(
            "llm-call",
            litellm.completion,
            model = "gpt-4o",
            messages=messages,
            tools=[{
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Get the current weather in a given location",
                    "parameters": WeatherRequest.model_json_schema(),
                },
            }],
        )
        response = result.choices[0].message
        messages.append(response)

        # No tool calls, return the response
        if not response.tool_calls:
            return response.content

        # Sequentially call each tool and add the result to messages
        for tool_call in response.tool_calls:
            if tool_call.function.name == "get_weather":
                tool_output = await ctx.run_typed(
                    "Get weather",
                    get_weather,
                    req=WeatherRequest.model_validate_json(
                        tool_call.function.arguments
                    ),
                )
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": tool_output,
                    }
                )

