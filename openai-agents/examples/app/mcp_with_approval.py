import restate

from agents import (
    Agent,
    HostedMCPTool,
    MCPToolApprovalRequest,
    MCPToolApprovalFunctionResult,
)
from openai.types.responses.tool_param import Mcp
from restate.ext.openai import restate_context, DurableRunner

from app.utils.models import ChatMessage
from app.utils.utils import request_mcp_approval

agent_service = restate.Service("McpWithApprovalsChat")


async def approve_func(req: MCPToolApprovalRequest) -> MCPToolApprovalFunctionResult:
    # Request human review
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
            ),
            on_approval_request=approve_func,
            # or use require_approval="never" in the tool_config to disable approvals
        )
    ],
)


@agent_service.handler()
async def message(_ctx: restate.Context, req: ChatMessage) -> str:
    result = await DurableRunner.run(agent, req.message)
    return result.final_output
