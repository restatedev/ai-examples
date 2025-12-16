from agents import Agent
from restate import VirtualObject, ObjectContext
from restate.ext.openai import DurableRunner

from app.utils.models import ChatMessage

chat = VirtualObject("Chat")


@chat.handler()
async def message(_ctx: ObjectContext, req: ChatMessage) -> dict:
    # Set use_restate_session=True to store the session in Restate's key-value store
    # Make sure you use a VirtualObject to enable this feature
    result = await DurableRunner.run(
        Agent(name="Assistant", instructions="You are a helpful assistant."),
        req.message,
        use_restate_session=True,
    )
    return result.final_output
