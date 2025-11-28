from typing import List

from agents import Agent, Runner, HostedMCPTool, TResponseInputItem, MCPToolApprovalRequest, \
    MCPToolApprovalFunctionResult
from openai.types.responses.tool_param import Mcp
from restate import VirtualObject, ObjectContext, ObjectSharedContext

from app.utils.middleware import Runner, RestateSession
from app.utils.models import ChatMessage
from app.utils.utils import request_human_review, request_mcp_approval

chat = VirtualObject("McpWithApprovalsChat")

async def approve_func(req: MCPToolApprovalRequest) -> MCPToolApprovalFunctionResult:
    restate_context = req.ctx_wrapper.context

    # Request human review
    approval_id, approval_promise = restate_context.awakeable(type_hint=bool)
    await restate_context.run_typed(
        "Approve MCP tool", request_mcp_approval, mcp_tool_name=req.data.name, awakeable_id=approval_id
    )
    # Wait for human approval
    approved = await approval_promise
    if not approved:
        return {"approve": approved, "reason": "User denied"}
    return {"approve": approved}



@chat.handler()
async def message(ctx: ObjectContext, chat_message: ChatMessage) -> str:

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
                        server_url="https://docs.restate.dev/mcp"
                    ),
                    on_approval_request=approve_func
                    # or use require_approval="never" in the tool_config to disable approvals
                )
            ],
        ),
        input=chat_message.message,
        session=RestateSession(),
        context=ctx
    )

    return result.final_output


@chat.handler(kind="shared")
async def get_history(_ctx: ObjectSharedContext) -> List[TResponseInputItem]:
    session = RestateSession()
    return await session.get_items()
