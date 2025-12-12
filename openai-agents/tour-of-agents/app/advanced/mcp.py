from typing import List

from agents import Agent, HostedMCPTool, TResponseInputItem, Runner
from openai.types.responses.tool_param import Mcp
from restate import VirtualObject, ObjectContext, ObjectSharedContext
from restate.ext.openai.runner_wrapper import RestateSession

from app.utils.models import ChatMessage

chat = VirtualObject("McpChat")


@chat.handler()
async def message(_ctx: ObjectContext, chat_message: ChatMessage) -> str:

    result = await Runner.run(
        Agent(
            name="Assistant",
            instructions="You are a helpful assistant.",
            tools=[
                HostedMCPTool(
                    tool_config=Mcp(
                        type="mcp",
                        server_label="restate_docs",
                        server_description="A knowledge base about Restate's documentation.",
                        server_url="https://docs.restate.dev/mcp",
                        require_approval="never",
                    ),
                )
            ],
        ),
        input=chat_message.message,
        session=RestateSession(),
    )
    return result.final_output


@chat.handler(kind="shared")
async def get_history(_ctx: ObjectSharedContext) -> List[TResponseInputItem]:
    return await RestateSession().get_items()
