from typing import List

from agents import (
    Agent,
    Runner,
    WebSearchTool,
    TResponseInputItem,
)
from restate import VirtualObject, ObjectContext, ObjectSharedContext

from app.utils.middleware import Runner, RestateSession
from app.utils.models import ChatMessage

chat = VirtualObject("WebsearchChat")


@chat.handler()
async def message(restate_context: ObjectContext, chat_message: ChatMessage) -> str:

    result = await Runner.run(
        Agent(
            name="Assistant",
            instructions="You are a helpful assistant.",
            tools=[
                WebSearchTool()
            ],
        ),
        input=chat_message.message,
        session=RestateSession(),
    )
    return result.final_output


@chat.handler(kind="shared")
async def get_history(_ctx: ObjectSharedContext) -> List[TResponseInputItem]:
    session = RestateSession()
    return await session.get_items()
