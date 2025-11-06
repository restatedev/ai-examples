import restate
from google.genai import types as genai_types
from pydantic import BaseModel

from middleware.middleware import durable_model_calls
from middleware.restate_runner import create_restate_runner
from google.adk.agents.llm_agent import Agent

APP_NAME = "agents"


class ChatMessage(BaseModel):
    message: str


chat = restate.VirtualObject("Chat")


@chat.handler()
async def message(ctx: restate.ObjectContext, chat_message: ChatMessage) -> str:
    user_id = "user"
    agent = Agent(
        model=durable_model_calls(ctx, "gemini-2.5-flash"),
        name="assistant",
        description="A helpful assistant that can answer questions.",
        instruction="You are a helpful assistant. Be concise and helpful.",
    )

    runner = await create_restate_runner(ctx, APP_NAME, user_id, agent)
    events = runner.run_async(
        user_id=user_id,
        session_id=ctx.key(),
        new_message=genai_types.Content(
            role="user", parts=[genai_types.Part.from_text(text=chat_message.message)]
        ),
    )

    final_response = ""
    async for event in events:
        if event.is_final_response() and event.content and event.content.parts:
            final_response = event.content.parts[0].text

    return final_response


@chat.handler(kind="shared")
async def get_history(ctx: restate.ObjectSharedContext):
    return await ctx.get("items") or []
