import restate

from agents import Agent, HostedMCPTool
from openai.types.responses.tool_param import Mcp
from restate.ext.openai import DurableRunner

from app.utils.models import ChatMessage


agent = Agent(
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
)

agent_service = restate.Service("McpChat")


@agent_service.handler()
async def message(_ctx: restate.Context, req: ChatMessage) -> str:
    result = await DurableRunner.run(agent, req.message)
    return result.final_output
