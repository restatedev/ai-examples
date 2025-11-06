import restate
from google.genai import types as genai_types
from app.utils.models import WeatherResponse, WeatherPrompt
from app.utils.utils import call_weather_api
from google.adk.tools.tool_context import ToolContext
from google.adk.agents.llm_agent import Agent
from middleware.middleware import durable_model_calls
from middleware.restate_runner import create_restate_runner
from middleware.restate_tools import restate_tools

APP_NAME = "agents"

agent_service = restate.VirtualObject("WeatherAgent")


async def get_weather(tool_context: ToolContext, city: str) -> WeatherResponse:
    """Get the current weather for a given city."""
    restate_context = tool_context.session.state["restate_context"]
    return await restate_context.run_typed("Get weather", call_weather_api, city=city)


@agent_service.handler()
async def run(ctx: restate.ObjectContext, prompt: WeatherPrompt) -> str:
    user_id = "user"

    agent = Agent(
        model=durable_model_calls(ctx, "gemini-2.5-flash"),
        name="weather_agent",
        description="Agent that provides weather updates for cities.",
        instruction="You are a helpful agent that provides weather updates. Use the get_weather tool to fetch current weather information.",
        tools=restate_tools(get_weather),
    )

    runner = await create_restate_runner(ctx, APP_NAME, user_id, agent)
    events = runner.run_async(
        user_id=user_id,
        session_id=ctx.key(),
        new_message=genai_types.Content(
            role="user", parts=[genai_types.Part.from_text(text=prompt.message)]
        ),
    )

    final_response = ""
    async for event in events:
        if event.is_final_response() and event.content and event.content.parts:
            final_response = event.content.parts[0].text

    return final_response
