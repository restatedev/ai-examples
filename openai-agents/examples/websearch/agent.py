import restate

from agents import Agent, WebSearchTool
from pydantic import BaseModel
from restate.ext.openai import DurableRunner


class ChatMessage(BaseModel):
    message: str = "Which use cases does Restate support?"


agent = Agent(
    name="Assistant",
    instructions="You are a helpful assistant.",
    tools=[WebSearchTool()],
)

agent_service = restate.Service("WebsearchChat")


@agent_service.handler()
async def message(_ctx: restate.Context, chat_message: ChatMessage) -> str:
    result = await DurableRunner.run(agent, chat_message.message)
    return result.final_output
