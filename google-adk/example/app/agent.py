import restate
from google.adk.agents.llm_agent import Agent
from google.adk.tools.tool_context import ToolContext
from google.adk.runners import Runner
from google.genai import types as genai_types
from pydantic import BaseModel

from app.utils.middleware import durable_model_calls
from app.utils.restate_session_service import RestateSessionService

APP_NAME = "agent_app"

async def get_current_time(tool_context: ToolContext, city: str) -> dict:
    """Returns the current time in a specified city."""
    restate_context = tool_context.session.state["restate_context"]

    # session needs to be Restate
    time_float = await restate_context.time()
    time_string = str(time_float)
    return {"status": "success", "city": city, "time": time_string}

class Prompt(BaseModel):
    msg: str = "What's the current time in New York?"

agent_service = restate.VirtualObject("agent")


@agent_service.handler()
async def run(ctx: restate.ObjectContext, prompt: Prompt) -> str:
    user_id = "test_user"

    session_service = RestateSessionService(ctx)
    await session_service.create_session(
        app_name=APP_NAME, user_id=user_id, session_id=ctx.key()
    )

    agent = Agent(
        model=durable_model_calls(ctx, 'gemini-2.5-flash'),
        name='time_agent',
        description="Tells the current time in a specified city.",
        instruction="You are a helpful assistant that tells the current time in cities. Use the 'get_current_time' tool for this purpose.",
        tools=[get_current_time],
    )

    runner = Runner(agent=agent, app_name=APP_NAME, session_service=session_service)

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