import restate
from agents import (
    Agent,
    RunConfig,
    Runner,
    function_tool,
    RunContextWrapper,
    ModelSettings,
)

from app.utils.middleware import DurableModelCalls, raise_restate_errors
from app.utils.models import ClaimPrompt
from app.utils.utils import (
    InsuranceClaim,
    request_human_review,
)


# <start_wf>
# Sub-workflow service for human approval
human_approval_workflow = restate.Service("HumanApprovalWorkflow")


@human_approval_workflow.handler("requestApproval")
async def request_approval(
    restate_context: restate.Context, claim: InsuranceClaim
) -> str:
    """Request human approval for a claim and wait for response."""
    # Create an awakeable that can be resolved via HTTP
    approval_id, approval_promise = restate_context.awakeable(type_hint=str)

    # Request human review
    await restate_context.run_typed(
        "Request review", request_human_review, claim=claim, awakeable_id=approval_id
    )

    # Wait for human approval
    return await approval_promise


# <end_wf>


# <start_here>
@function_tool(failure_error_function=raise_restate_errors)
async def human_approval(
    wrapper: RunContextWrapper[restate.Context], claim: InsuranceClaim
) -> str:
    """Ask for human approval for high-value claims using sub-workflow."""
    restate_context = wrapper.context

    # Call the human approval sub-workflow
    return await restate_context.service_call(request_approval, claim)


# <end_here>


sub_workflow_agent = Agent[restate.Context](
    name="ClaimApprovalAgent",
    instructions="You are an insurance claim evaluation agent. "
    "Use these rules: if the amount is more than 1000, ask for human approval; "
    "if the amount is less than 1000, decide by yourself.",
    tools=[human_approval],
)


agent_service = restate.Service("SubWorkflowClaimApprovalAgent")


@agent_service.handler()
async def run(restate_context: restate.Context, prompt: ClaimPrompt) -> str:
    result = await Runner.run(
        sub_workflow_agent,
        input=prompt.message,
        context=restate_context,
        run_config=RunConfig(
            model="gpt-4o",
            model_provider=DurableModelCalls(restate_context),
            model_settings=ModelSettings(parallel_tool_calls=False),
        ),
    )

    return result.final_output
