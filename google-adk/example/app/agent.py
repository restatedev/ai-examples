import restate
from datetime import datetime
from google.adk.agents.llm_agent import Agent
from google.adk.tools.tool_context import ToolContext
from google.adk.runners import Runner
from google.genai import types as genai_types
from pydantic import BaseModel

from app.utils.middleware import durable_model_calls
from app.utils.restate_runner import RestateRunner
from app.utils.restate_session_service import RestateSessionService, get_restate_context
from app.utils.restate_tools import restate_tools

APP_NAME = "agents"

async def get_weather(tool_context: ToolContext, city: str) -> dict:
    """Retrieves the current weather report for a specified city."""
    restate_context = get_restate_context(tool_context)

    def call_weather_api():
        if city.lower() == "new york":
            return {
                "status": "success",
                "report": (
                    "The weather in New York is sunny with a temperature of 25 degrees"
                    " Celsius (77 degrees Fahrenheit)."
                ),
            }
        else:
            return {
                "status": "error",
                "error_message": f"Weather information for '{city}' is not available.",
            }

    return await restate_context.run_typed("get weather", lambda: call_weather_api())



class Prompt(BaseModel):
    msg: str = "What's the current time in New York?"

agent_service = restate.VirtualObject("agent")


@agent_service.handler()
async def run(ctx: restate.ObjectContext, prompt: Prompt) -> str:
    user_id = "test_user"

    agent = Agent(
        model=durable_model_calls(ctx, 'gemini-2.5-flash'),
        name='weather_time_agent',
        description="Agent to answer questions about the weather in a city.",
        instruction="You are a helpful agent who can answer user questions about the weather in a city.",
        tools=restate_tools(get_weather),
    )

    session_service = RestateSessionService(ctx)
    await session_service.create_session(
        app_name=APP_NAME, user_id=user_id, session_id=ctx.key()
    )

    runner = RestateRunner(restate_context=ctx, agent=agent, app_name=APP_NAME, session_service=session_service)

    events = runner.run_async(
        user_id=user_id,
        session_id=ctx.key(),
        new_message=genai_types.Content(
            role="user",
            parts=[genai_types.Part.from_text(text=prompt.msg)]
        )
    )

    final_response = ""
    async for event in events:
        if event.is_final_response() and event.content and event.content.parts:
            final_response = event.content.parts[0].text

    return final_response