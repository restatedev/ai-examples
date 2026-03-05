import json
import restate
from pydantic import BaseModel
from litellm import acompletion
from litellm.types.utils import Message


class WeatherPrompt(BaseModel):
    message: str = "What is the weather in San Francisco?"


# TOOL IMPLEMENTATION
async def get_weather(city: str) -> str:
    return json.dumps({"temperature": 23, "condition": "Sunny"})


# TOOL DEFINITIONS
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get the current weather for a city",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "The city name"}
                },
                "required": ["city"],
            },
        },
    }
]

# AGENT SERVICE
agent_service = restate.Service("agent")


@agent_service.handler()
async def run(ctx: restate.Context, message: WeatherPrompt) -> str:
    """Handle a user message, calling tools until a final answer is ready."""
    messages = [
        {"role": "system", "content": "You are a helpful weather assistant."},
        {"role": "user", "content": message.message},
    ]

    while True:
        # Call the LLM
        async def call_llm() -> Message:
            resp = await acompletion(
                model="gpt-4o-mini", messages=messages, tools=TOOLS
            )
            return resp.choices[0].message

        response = await ctx.run("LLM call", call_llm)

        messages.append(response.model_dump())

        if not response.tool_calls:
            return response.content

        for tool_call in response.tool_calls:
            city = json.loads(tool_call.function.arguments).get("city", "")
            result = await ctx.run_typed(f"get_weather {city}", get_weather, city=city)
            messages.append(
                {"role": "tool", "tool_call_id": tool_call.id, "content": result}
            )
