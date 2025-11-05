import restate
from google.adk.agents.llm_agent import Agent
from google.genai import types as genai_types
from pydantic import BaseModel

from middleware.deterministic_id import deterministic_uuid
from middleware.middleware import durable_model_calls
from middleware.restate_runner import RestateRunner
from middleware.restate_session_service import RestateSessionService
from google.adk.agents.llm_agent import Agent

APP_NAME = "agents"

class ChatMessage(BaseModel):
    message: str

chat = restate.VirtualObject("Chat")


@chat.handler()
async def message(ctx: restate.ObjectContext, chat_message: ChatMessage) -> str:
    user_id = "user"
    agent = Agent(
        model=durable_model_calls(ctx, 'gemini-2.5-flash'),
        name='assistant',
        description="A helpful assistant that can answer questions.",
        instruction="You are a helpful assistant. Be concise and helpful.",
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
            parts=[genai_types.Part.from_text(text=chat_message.message)]
        )
    )

    final_response = ""
    async for event in events:
        if event.is_final_response() and event.content and event.content.parts:
            final_response = event.content.parts[0].text

    return final_response


@chat.handler(kind="shared")
async def get_history(ctx: restate.ObjectSharedContext):
    return await ctx.get("items") or []
