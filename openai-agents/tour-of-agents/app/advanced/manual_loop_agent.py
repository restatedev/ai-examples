import restate
from openai.types.chat import (
    ChatCompletion,
    ChatCompletionMessageParam,
    ChatCompletionMessageFunctionToolCall,
    ChatCompletionToolMessageParam,
    ChatCompletionUserMessageParam,
)
from pydantic import BaseModel
from restate import Context
from openai import OpenAI, pydantic_function_tool

from app.utils.models import WeatherRequest
from app.utils.utils import fetch_weather, as_chat_completion_param

# Initialize OpenAI client
client = OpenAI()

# Tool definitions
TOOLS = [
    pydantic_function_tool(
        WeatherRequest,
        name="get_weather",
        description="Get the current weather in a given location",
    )
]


manual_loop_agent = restate.Service("ManualLoopAgent")


class MultiWeatherPrompt(BaseModel):
    message: str = "What is the weather like in New York and San Francisco?"


@manual_loop_agent.handler()
async def run(ctx: Context, prompt: MultiWeatherPrompt) -> str | None:
    """Main agent loop with tool calling"""
    messages: list[ChatCompletionMessageParam] = [
        ChatCompletionUserMessageParam(role="user", content=prompt.message)
    ]

    while True:
        # Call OpenAI with durable execution
        def llm_call() -> ChatCompletion:
            return client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                tools=TOOLS,
            )

        response = await ctx.run_typed(
            "llm-call",
            llm_call,
            restate.RunOptions(
                max_attempts=3
            ),  # To avoid using too many credits on infinite retries during development
        )

        # Save function call outputs for subsequent requests
        assistant_message = response.choices[0].message
        messages.append(as_chat_completion_param(assistant_message))

        if not assistant_message.tool_calls:
            return assistant_message.content

        # Check if we need to call tools
        for tool_call in assistant_message.tool_calls:
            if (
                isinstance(tool_call, ChatCompletionMessageFunctionToolCall)
                and tool_call.function.name == "get_weather"
            ):
                req = WeatherRequest.model_validate_json(tool_call.function.arguments)
                tool_output = await ctx.run_typed(
                    "Get weather", fetch_weather, city=req.city
                )

                # Add tool response to messages
                messages.append(
                    ChatCompletionToolMessageParam(
                        role="tool",
                        tool_call_id=tool_call.id,
                        content=tool_output.model_dump_json(),
                    )
                )
