import restate
from agents import Agent, RunConfig, Runner, function_tool, RunContextWrapper

from app.middleware import DurableModelCalls
from app.utils import (
    InsuranceClaim,
    request_human_review,
)


# Sub-workflow service for human approval
human_approval_workflow = restate.Service("HumanApprovalWorkflow")


@human_approval_workflow.handler()
async def request_approval(restate_context: restate.Context, claim: InsuranceClaim) -> bool:
    """Request human approval for a claim and wait for response."""
    # Create an awakeable that can be resolved by external input
    approval_awakeable = restate_context.awakeable()

    # Request human review
    await restate_context.run_typed(
        "Request human review",
        request_human_review,
        message=f"Please review: {claim.model_dump_json()}",
        awakeable_id=approval_awakeable.id
    )

    # Wait for the awakeable to be resolved
    return await approval_awakeable.promise


@human_approval_workflow.handler()
async def resolve_approval(restate_context: restate.Context, data: dict) -> str:
    """Resolve a pending human approval."""
    awakeable_id = data["awakeable_id"]
    approval = data["approval"]  # boolean

    # Resolve the awakeable
    restate_context.resolve_awakeable(awakeable_id, approval)

    return f"Approval {'granted' if approval else 'denied'} for awakeable {awakeable_id}"


@function_tool
async def human_approval(
    wrapper: RunContextWrapper[restate.Context], claim: InsuranceClaim
) -> str:
    """Ask for human approval for high-value claims using sub-workflow."""
    restate_context = wrapper.context

    # Call the human approval sub-workflow
    approval_result = await restate_context.service_client(human_approval_workflow).request_approval(claim)

    return f"Human approval result: {'Approved' if approval_result else 'Rejected'}"


sub_workflow_agent = Agent[restate.Context](
    name="SubWorkflowClaimApprovalAgent",
    instructions="You are an insurance claim evaluation agent that uses sub-workflows for human approval. Use these rules: if the amount is more than 1000, ask for human approval; if the amount is less than 1000, decide by yourself.",
    tools=[human_approval],
)


agent_service = restate.Service("SubWorkflowClaimApprovalAgent")


@agent_service.handler()
async def run(restate_context: restate.Context, message: str) -> str:
    result = await Runner.run(
        sub_workflow_agent,
        input=message,
        context=restate_context,
        run_config=RunConfig(
            model="gpt-4o", model_provider=DurableModelCalls(restate_context)
        ),
    )

    return result.final_output