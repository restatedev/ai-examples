import restate
from agents import Agent, RunConfig, Runner, function_tool, RunContextWrapper

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
    approval_id, approval_promise = restate_context.awakeable(type_hint=str)

    # Request human review
    await restate_context.run_typed(
        "Request human review",
        request_human_review,
        message=f"Please review: {claim.model_dump_json()}",
        awakeable_id=approval_id
    )

    # Wait for human approval
    approval_result = await approval_promise

    return f"Human approval result: {'Approved' if approval_result else 'Rejected'}"


claim_approval_agent = Agent[restate.Context](
    name="HumanClaimApprovalAgent",
    instructions="You are an insurance claim evaluation agent. "
                 "Use these rules: if the amount is more than 1000, ask for human approval; "
                 "if the amount is less than 1000, decide by yourself.",
    tools=[human_approval],
)


agent_service = restate.Service("HumanClaimApprovalAgent")


@agent_service.handler()
async def run(restate_context: restate.Context, message: str) -> str:
    result = await Runner.run(
        claim_approval_agent,
        input=message,
        context=restate_context,
        run_config=RunConfig(
            model="gpt-4o", model_provider=DurableModelCalls(restate_context)
        ),
    )

    return result.final_output


@agent_service.handler()
async def resolve_approval(restate_context: restate.Context, data: dict) -> str:
    """Resolve a pending human approval."""
    awakeable_id = data["awakeable_id"]
    approval = data["approval"]  # boolean

    # Resolve the awakeable
    restate_context.resolve_awakeable(awakeable_id, approval)

    return f"Approval {'granted' if approval else 'denied'} for awakeable {awakeable_id}"