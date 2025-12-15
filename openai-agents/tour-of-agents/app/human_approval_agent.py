import restate

from agents import Agent, function_tool
from restate.ext.openai import restate_context, DurableRunner

from app.utils.models import ClaimPrompt
from app.utils.utils import (
    InsuranceClaim,
    request_human_review,
)


# <start_here>
@function_tool
async def human_approval(claim: InsuranceClaim) -> str:
    """Ask for human approval for high-value claims."""

    # Create an awakeable for human approval
    approval_id, approval_promise = restate_context().awakeable(type_hint=str)

    # Request human review
    await restate_context().run_typed(
        "Request review", request_human_review, claim=claim, awakeable_id=approval_id
    )

    # Wait for human approval
    return await approval_promise


# <end_here>


agent = Agent(
    name="HumanClaimApprovalAgent",
    instructions="You are an insurance claim evaluation agent. "
    "Use these rules: if the amount is more than 1000, ask for human approval; "
    "if the amount is less than 1000, decide by yourself.",
    tools=[human_approval],
)


agent_service = restate.Service("HumanClaimApprovalAgent")


@agent_service.handler()
async def run(_ctx: restate.Context, req: ClaimPrompt) -> str:
    result = await DurableRunner.run(agent, req.message)
    return result.final_output
