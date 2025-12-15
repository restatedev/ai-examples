import restate
from agents import Agent, function_tool
from restate.ext.openai import restate_context, DurableRunner

from app.utils.models import ClaimPrompt
from app.utils.utils import (
    InsuranceClaim,
    request_human_review,
)


# <start_wf>
# Sub-workflow service for human approval
human_approval_workflow = restate.Service("HumanApprovalWorkflow")


@human_approval_workflow.handler()
async def review(ctx: restate.Context, claim: InsuranceClaim) -> str:
    """Request human approval for a claim and wait for response."""
    # Create an awakeable that can be resolved via HTTP
    approval_id, approval_promise = ctx.awakeable(type_hint=str)

    # Request human review
    await ctx.run_typed(
        "Request review", request_human_review, claim=claim, awakeable_id=approval_id
    )

    # Wait for human approval
    return await approval_promise


# <end_wf>


# <start_here>
@function_tool
async def human_approval(claim: InsuranceClaim) -> str:
    """Ask for human approval for high-value claims using sub-workflow."""
    return await restate_context().service_call(review, claim)


# <end_here>


agent = Agent(
    name="ClaimApprovalAgent",
    instructions="You are an insurance claim evaluation agent. "
    "Use these rules: if the amount is more than 1000, ask for human approval; "
    "if the amount is less than 1000, decide by yourself.",
    tools=[human_approval],
)


agent_service = restate.Service("SubWorkflowClaimApprovalAgent")


@agent_service.handler()
async def run(_ctx: restate.Context, req: ClaimPrompt) -> str:
    result = await DurableRunner.run(agent, req.message)
    return result.final_output
