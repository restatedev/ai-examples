import restate
from restate import Context
from openai import OpenAI
import json

from app.utils.models import WeatherRequest, WeatherResponse
from app.utils.utils import fetch_weather

# Initialize OpenAI client
client = OpenAI()

# Tool definitions for OpenAI
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "getWeather",
            "description": "Get the current weather in a given location",
            "parameters": WeatherRequest.model_json_schema()
        }
    }
]


async def get_weather(restate_context: Context, req: WeatherRequest) -> WeatherResponse:
    """Get the current weather in a given location"""
    return await restate_context.run_typed("Get weather", fetch_weather, city=req.city)


manual_loop_agent = restate.Service("ManualLoopAgent")


@manual_loop_agent.handler()
async def run(ctx: Context, prompt: str) -> str:
    """Main agent loop with tool calling"""
    messages = [{"role": "user", "content": prompt}]

    while True:
        # Call OpenAI with durable execution
        response = await ctx.run(
            "llm-call",
            lambda: client.responses.completions.create(
                model="gpt-4o",
                messages=messages,
                tools=TOOLS,
                tool_choice="auto"
            )
        )

        response_message = response.choices[0].message
        messages.append(response_message.model_dump(exclude_unset=True))

        # Check if we need to call tools
        if response_message.tool_calls:
            # Handle all tool calls
            for tool_call in response_message.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)

                if function_name == "getWeather":
                    tool_output = await get_weather(ctx, function_args["city"])

                    # Add tool response to messages
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(tool_output)
                    })
                # Handle other tool calls here

        else:
            # No more tool calls, return final response
            return response_message.content