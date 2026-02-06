import restate

from agents import Agent, HostedMCPTool, MCPToolApprovalRequest, MCPToolApprovalFunctionResult
from openai.types.responses.tool_param import Mcp
from pydantic import BaseModel
from restate.ext.openai import restate_context, DurableRunner

from utils import request_mcp_approval


class ChatMessage(BaseModel):
    message: str = "Which use cases does Restate support?"


# --- MCP Agent (no approval) ---

mcp_agent = Agent(
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

mcp_service = restate.Service("McpChat")


@mcp_service.handler()
async def message(_ctx: restate.Context, req: ChatMessage) -> str:
    result = await DurableRunner.run(mcp_agent, req.message)
    return result.final_output


# --- MCP Agent (with approval) ---


async def approve_func(req: MCPToolApprovalRequest) -> MCPToolApprovalFunctionResult:
    # Request human review
    print("I am here")
    approval_id, approval_promise = restate_context().awakeable(type_hint=bool)
    await restate_context().run_typed(
        "Approve MCP tool",
        request_mcp_approval,
        mcp_tool_name=req.data.name,
        awakeable_id=approval_id,
    )
    # Wait for human approval
    approved = await approval_promise
    if not approved:
        return {"approve": approved, "reason": "User denied"}
    return {"approve": approved}


mcp_with_approval_agent = Agent(
    name="Assistant",
    instructions="You are a helpful assistant. Use tools.",
    tools=[
        HostedMCPTool(
            tool_config=Mcp(
                type="mcp",
                server_label="restate_docs",
                server_description="A knowledge base about Restate's documentation.",
                server_url="https://docs.restate.dev/mcp",
                require_approval="always"
            ),
            on_approval_request=approve_func,
        )
    ],
)


@mcp_service.handler()
async def message_with_approval(_ctx: restate.Context, req: ChatMessage) -> str:
    result = await DurableRunner.run(mcp_with_approval_agent, req.message)
    return result.final_output
