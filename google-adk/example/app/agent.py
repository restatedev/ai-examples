import restate
from google.adk.agents.llm_agent import Agent
from google.adk.runners import Runner, RunConfig
from google.adk.agents.run_config import StreamingMode
from google.adk.sessions import InMemorySessionService
from google.adk.models.google_llm import Gemini
from google.genai import types as genai_types
from pydantic import BaseModel

from app.middleware import durable_model_calls


class Prompt(BaseModel):
    msg: str = "What's the current time in New York?"

agent_service = restate.Service("agent")


@agent_service.handler()
async def run(ctx: restate.Context, prompt: Prompt) -> str:

    async def get_current_time(city: str) -> dict:
        """Returns the current time in a specified city."""
        time_float = await ctx.time()
        time_string = str(time_float)
        return {"status": "success", "city": city, "time": time_string}


    session_service = InMemorySessionService()
    await session_service.create_session(
        app_name="app", user_id="test_user", session_id="test_session"
    )

    root_agent = Agent(
        model=durable_model_calls(ctx, Gemini()),
        name='root_agent',
        description="Tells the current time in a specified city.",
        instruction="You are a helpful assistant that tells the current time in cities. Use the 'get_current_time' tool for this purpose.",
        tools=[get_current_time],
    )

    runner = Runner(agent=root_agent, app_name="app", session_service=session_service)

    events = runner.run_async(
        user_id="test_user",
        session_id="test_session",
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