from datetime import timedelta

import restate
from agents import Agent, RunConfig, Runner, function_tool, RunContextWrapper, ModelSettings

from app.utils.middleware import DurableModelCalls
from app.utils.utils import (
    InsuranceClaim,
    request_human_review,
)


@function_tool
async def human_approval(
    wrapper: RunContextWrapper[restate.Context], claim: InsuranceClaim
) -> str:
    """Ask for human approval for high-value claims."""
    restate_context = wrapper.context

    # Create an awakeable for human approval
    approval_id, approval_promise = restate_context.awakeable(type_hint=bool)

    # Request human review
    await restate_context.run_typed(
        "Request human review",
        request_human_review,
        message=f"Please review: {claim.model_dump_json()}",
        awakeable_id=approval_id
    )

    # <start_here>
    # Wait for human approval for at most 3 hours to reach our SLA
    match await restate.select(
        approval=approval_promise,
        timeout=restate_context.sleep(timedelta(hours=3)),
    ):
        case ["approval", approved]:
            return "Approved" if approved else "Rejected"
        case _:
            return "Approval timed out - Evaluate with AI"
    # <end_here>


claim_approval_agent = Agent[restate.Context](
    name="HumanClaimApprovalAgent",
    instructions="You are an insurance claim evaluation agent. "
                 "Use these rules: if the amount is more than 1000, ask for human approval; "
                 "if the amount is less than 1000, decide by yourself.",
    tools=[human_approval],
)


agent_service = restate.Service("HumanClaimApprovalWithTimeoutsAgent")


@agent_service.handler()
async def run(restate_context: restate.Context, message: str) -> str:
    result = await Runner.run(
        claim_approval_agent,
        input=message,
        context=restate_context,
        run_config=RunConfig(
            model="gpt-4o",
            model_provider=DurableModelCalls(restate_context, max_retries=3),
            model_settings=ModelSettings(parallel_tool_calls=False)
        ),
    )

    return result.final_output