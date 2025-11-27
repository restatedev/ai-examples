from typing import List

from agents import Agent, Runner, WebSearchTool, HostedMCPTool, TResponseInputItem
from openai.types.responses.tool_param import Mcp
from restate import VirtualObject, ObjectContext, ObjectSharedContext

from app.utils.middleware import Runner, RestateSession
from app.utils.models import ChatMessage

chat = VirtualObject("McpChat")


@chat.handler()
async def message(_ctx: ObjectContext, chat_message: ChatMessage) -> dict:
    result = await Runner.run(
        Agent(
            name="Assistant",
            instructions="You are a helpful assistant.",
            tools = [
                HostedMCPTool(
                    tool_config=Mcp(
                        type="mcp",
                        server_label="restate_docs",
                        server_description="A knowledge base about Restate's documentation.",
                        server_url="https://docs.restate.dev/mcp",
                    )
                ),
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
