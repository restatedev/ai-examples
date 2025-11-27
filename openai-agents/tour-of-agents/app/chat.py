from agents import Agent, Runner, WebSearchTool
from restate import VirtualObject, ObjectContext, ObjectSharedContext

from app.utils.middleware import Runner, RestateSession
from app.utils.models import ChatMessage

chat = VirtualObject("Chat")


@chat.handler()
async def message(_ctx: ObjectContext, chat_message: ChatMessage) -> dict:
    result = await Runner.run(
        Agent(name="Assistant", instructions="You are a helpful assistant."),
        input=chat_message.message,
        session=RestateSession(),
    )
    return result.final_output


@chat.handler(kind="shared")
async def get_history(_ctx: ObjectSharedContext):
    session = RestateSession()
    return session.get_items()
