from typing import List

from agents import Agent, Runner, TResponseInputItem
from restate import VirtualObject, ObjectContext, ObjectSharedContext
from restate.ext.openai.runner_wrapper import DurableOpenAIAgents, RestateSession

from app.utils.models import ChatMessage

chat = VirtualObject("Chat", invocation_context_managers=[DurableOpenAIAgents])


@chat.handler()
async def message(_ctx: ObjectContext, chat_message: ChatMessage) -> dict:
    result = await Runner.run(
        Agent(name="Assistant", instructions="You are a helpful assistant."),
        input=chat_message.message,
        session=RestateSession(),
    )
    return result.final_output


@chat.handler(kind="shared")
async def get_history(_ctx: ObjectSharedContext) -> List[TResponseInputItem]:
    return await RestateSession().get_items()
