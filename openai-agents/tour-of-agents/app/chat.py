from typing import List

from agents import Agent, TResponseInputItem
from restate import VirtualObject, ObjectContext, ObjectSharedContext
from restate.ext.openai import DurableRunner, RestateSession

from app.utils.models import ChatMessage

chat = VirtualObject("Chat")


@chat.handler()
async def message(_ctx: ObjectContext, req: ChatMessage) -> dict:
    result = await DurableRunner.run(
        Agent(name="Assistant", instructions="You are a helpful assistant."),
        req.message,
        session=RestateSession(),
    )
    return result.final_output


@chat.handler(kind="shared")
async def get_history(_ctx: ObjectSharedContext) -> List[TResponseInputItem]:
    return await RestateSession().get_items()
