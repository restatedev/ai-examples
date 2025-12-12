from datetime import timedelta

import restate
from agents import (
    Agent,
    Runner,
    function_tool,
)
from restate.ext.openai import restate_context, DurableOpenAIAgents

from app.utils.models import ClaimPrompt
from app.utils.utils import (
    InsuranceClaim,
    request_human_review,
)


@function_tool
async def human_approval(claim: InsuranceClaim) -> str:
    """Ask for human approval for high-value claims."""
    # Create an awakeable for human approval
    approval_id, approval_promise = restate_context().awakeable(type_hint=bool)

    # Request human review
    await restate_context().run_typed(
        "Request review", request_human_review, claim=claim, awakeable_id=approval_id
    )

    # <start_here>
    # Wait for human approval for at most 3 hours to reach our SLA
    match await restate.select(
        approval=approval_promise,
        timeout=restate_context().sleep(timedelta(seconds=3)),
    ):
        case ["approval", approved]:
            return "Approved" if approved else "Rejected"
        case _:
            return "Approval timed out - Evaluate with AI"
    # <end_here>


claim_approval_agent = Agent(
    name="HumanClaimApprovalAgent",
    instructions="You are an insurance claim evaluation agent. "
    "Use these rules: if the amount is more than 1000, ask for human approval; "
    "if the amount is less than 1000, decide by yourself.",
    tools=[human_approval],
)


agent_service = restate.Service(
    "HumanClaimApprovalWithTimeoutsAgent",
    invocation_context_managers=[DurableOpenAIAgents],
)


@agent_service.handler()
async def run(_ctx: restate.Context, prompt: ClaimPrompt) -> str:
    result = await Runner.run(claim_approval_agent, input=prompt.message)
    return result.final_output
