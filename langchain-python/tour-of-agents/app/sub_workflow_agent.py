"""Workflow-as-tool: a tool that calls a separate Restate service which
contains the human-approval logic.

Putting the HITL flow in its own service lets you scale, audit, and version
it independently of the agent."""

import restate
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain_core.tools import tool

from restate.ext.langchain import RestateMiddleware, restate_context

from utils.models import ClaimPrompt, InsuranceClaim
from utils.utils import request_human_review


# <start_wf>
# Sub-workflow service for human approval.
human_approval_workflow = restate.Service("HumanApprovalWorkflow")


@human_approval_workflow.handler()
async def review(ctx: restate.Context, claim: InsuranceClaim) -> str:
    """Request human approval for a claim and wait for response."""
    approval_id, approval_promise = ctx.awakeable(type_hint=str)

    await ctx.run_typed(
        "Request review", request_human_review, claim=claim, awakeable_id=approval_id
    )

    return await approval_promise


# <end_wf>


# <start_here>
@tool
async def human_approval(claim: InsuranceClaim) -> str:
    """Ask for human approval for high-value claims."""
    return await restate_context().service_call(review, claim)


# <end_here>


agent = create_agent(
    model=init_chat_model("openai:gpt-4o-mini"),
    tools=[human_approval],
    system_prompt=(
        "You are an insurance claim evaluation agent. Use these rules:\n"
        "- if the amount is more than 1000, ask for human approval using tools;\n"
        "- if the amount is less than 1000, decide by yourself."
    ),
    middleware=[RestateMiddleware()],
)


agent_service = restate.Service("SubWorkflowClaimAgent")


@agent_service.handler()
async def run(_ctx: restate.Context, req: ClaimPrompt) -> str:
    result = await agent.ainvoke({"messages": [{"role": "user", "content": req.message}]})
    return result["messages"][-1].content


if __name__ == "__main__":
    import asyncio

    import hypercorn
    import hypercorn.asyncio

    app = restate.app(services=[agent_service, human_approval_workflow])
    conf = hypercorn.Config()
    conf.bind = ["0.0.0.0:9080"]
    asyncio.run(hypercorn.asyncio.serve(app, conf))
