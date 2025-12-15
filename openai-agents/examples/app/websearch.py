import restate

from agents import Agent, WebSearchTool
from restate import ObjectContext
from restate.ext.openai import DurableRunner

from app.utils.models import ChatMessage

agent = Agent(
    name="Assistant",
    instructions="You are a helpful assistant.",
    tools=[WebSearchTool()],
)

agent_service = restate.Service("WebsearchChat")


@agent_service.handler()
async def message(_ctx: ObjectContext, chat_message: ChatMessage) -> str:
    result = await DurableRunner.run(agent, chat_message.message)
    return result.final_output
