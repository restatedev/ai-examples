import restate
from openai.types.chat import ChatCompletion
from openai.types.responses import Response
from pydantic import BaseModel
from restate import Context
from openai import OpenAI
import json

from app.utils.models import WeatherRequest, WeatherResponse
from app.utils.utils import fetch_weather

# Initialize OpenAI client
client = OpenAI()

# Tool definitions
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "parameters": WeatherRequest.model_json_schema(),
            "description": "Get the current weather in a given location"
        }
    }
]


async def get_weather(restate_context: Context, req: WeatherRequest) -> WeatherResponse:
    """Get the current weather in a given location"""
    return await restate_context.run_typed("Get weather", fetch_weather, city=req.city)


manual_loop_agent = restate.Service("ManualLoopAgent")


class MultiWeatherPrompt(BaseModel):
    message: str = "What is the weather like in New York and San Francisco?"

@manual_loop_agent.handler()
async def run(ctx: Context, prompt: MultiWeatherPrompt) -> str:
    """Main agent loop with tool calling"""
    messages = [{"role": "user", "content": prompt.message}]

    while True:
        # Call OpenAI with durable execution
        response = await ctx.run_typed(
            "llm-call",
            client.chat.completions.create,
            restate.RunOptions(max_attempts=3,
                           type_hint=ChatCompletion),  # To avoid using too many credits on infinite retries during development
            model="gpt-4o",
            tools=TOOLS,
            messages=messages,
        )

        # Save function call outputs for subsequent requests
        assistant_message = response.choices[0].message
        messages.append(assistant_message)

        if not assistant_message.tool_calls:
            return assistant_message.content

        # Check if we need to call tools
        for tool_call in assistant_message.tool_calls:
            if tool_call.function.name == "get_weather":
                tool_output = await get_weather(ctx, WeatherRequest(**json.loads(tool_call.function.arguments)))

                # Add tool response to messages
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": tool_output.model_dump_json()
                })