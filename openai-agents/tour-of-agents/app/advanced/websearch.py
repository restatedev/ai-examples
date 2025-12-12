from typing import List

from agents import (
    Agent,
    Runner,
    WebSearchTool,
    TResponseInputItem,
)
from restate import VirtualObject, ObjectContext, ObjectSharedContext
from restate.ext.openai.runner_wrapper import RestateSession, DurableOpenAIAgents

from app.utils.models import ChatMessage

chat = VirtualObject("WebsearchChat", invocation_context_managers=[DurableOpenAIAgents])


@chat.handler()
async def message(_ctx: ObjectContext, chat_message: ChatMessage) -> str:

    result = await Runner.run(
        Agent(
            name="Assistant",
            instructions="You are a helpful assistant.",
            tools=[WebSearchTool()],
        ),
        input=chat_message.message,
        session=RestateSession(),
    )
    return result.final_output


@chat.handler(kind="shared")
async def get_history(_ctx: ObjectSharedContext) -> List[TResponseInputItem]:
    return await RestateSession().get_items()
