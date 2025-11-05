import restate
from google.adk.agents.llm_agent import Agent
from google.adk.tools.tool_context import ToolContext
from google.genai import types as genai_types
from pydantic import BaseModel

from middleware.middleware import durable_model_calls
from middleware.restate_runner import RestateRunner
from middleware.restate_session_service import RestateSessionService
from middleware.restate_tools import restate_tools

APP_NAME = "agents"


class ClaimPrompt(BaseModel):
    message: str


class InsuranceClaim(BaseModel):
    claim_id: str
    claim_type: str
    amount: float
    description: str


def request_human_review(claim: InsuranceClaim, awakeable_id: str):
    """Simulate requesting human review (normally would send to external system)."""
    print(
        f"Human review requested for claim {claim.claim_id} (${claim.amount}) - awakeable_id: {awakeable_id}"
    )
    return f"Review requested for claim {claim.claim_id}"


# <start_wf>
# Sub-workflow service for human approval
human_approval_workflow = restate.Service("HumanApprovalWorkflow")


@human_approval_workflow.handler()
async def request_approval(ctx: restate.Context, claim: InsuranceClaim) -> str:
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
async def human_approval(
    tool_context: ToolContext,
    claim_id: str,
    claim_type: str,
    amount: float,
    description: str,
) -> str:
    """Ask for human approval for high-value claims using sub-workflow."""
    restate_context = tool_context.session.state["restate_context"]

    claim = InsuranceClaim(
        claim_id=claim_id, claim_type=claim_type, amount=amount, description=description
    )

    # Call the human approval sub-workflow
    return await restate_context.service_call(request_approval, claim)


# <end_here>


agent_service = restate.VirtualObject("SubWorkflowClaimApprovalAgent")


@agent_service.handler()
async def run(ctx: restate.ObjectContext, prompt: ClaimPrompt) -> str:
    user_id = "user"

    sub_workflow_agent = Agent(
        model=durable_model_calls(ctx, "gemini-2.5-flash"),
        name="sub_workflow_claim_agent",
        description="Insurance claim evaluation agent that uses sub-workflows for human approval.",
        instruction="You are an insurance claim evaluation agent. Use these rules: if the amount is more than 1000, ask for human approval; if the amount is less than 1000, decide by yourself.",
        tools=restate_tools(human_approval),
    )

    session_service = RestateSessionService(ctx)
    await session_service.create_session(
        app_name=APP_NAME, user_id=user_id, session_id=ctx.key()
    )

    runner = RestateRunner(
        restate_context=ctx,
        agent=sub_workflow_agent,
        app_name=APP_NAME,
        session_service=session_service,
    )

    events = runner.run_async(
        user_id=user_id,
        session_id=ctx.key(),
        new_message=genai_types.Content(
            role="user", parts=[genai_types.Part.from_text(text=prompt.message)]
        ),
    )

    final_response = ""
    async for event in events:
        if event.is_final_response() and event.content and event.content.parts:
            final_response = event.content.parts[0].text

    return final_response
