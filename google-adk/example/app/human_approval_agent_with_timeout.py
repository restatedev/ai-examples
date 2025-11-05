from datetime import timedelta

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

async def request_human_review(claim_id: str, amount: float, description: str, awakeable_id: str) -> str:
    """Simulate requesting human review (normally would send to external system)."""
    print(f"Human review requested for claim {claim_id} (${amount}) - awakeable_id: {awakeable_id}")
    return f"Review requested for claim {claim_id}"


async def human_approval(tool_context: ToolContext, claim_id: str, amount: float, description: str) -> str:
    """Ask for human approval for high-value claims."""
    restate_context = tool_context.session.state["restate_context"]

    # Create an awakeable for human approval
    approval_id, approval_promise = restate_context.awakeable(type_hint=str)

    # Request human review
    await restate_context.run_typed(
        "Request review", request_human_review, claim_id=claim_id, amount=amount, description=description, awakeable_id=approval_id
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


agent_service = restate.VirtualObject("HumanClaimApprovalWithTimeoutsAgent")


@agent_service.handler()
async def run(ctx: restate.ObjectContext, prompt: ClaimPrompt) -> str:
    user_id = "user"

    agent = Agent(
        model=durable_model_calls(ctx, 'gemini-2.5-flash'),
        name='claim_approval_with_timeout_agent',
        description="Insurance claim evaluation agent with timeout handling for human approval workflows.",
        instruction="You are an insurance claim evaluation agent. Use these rules: if the amount is more than 1000, ask for human approval; if the amount is less than 1000, decide by yourself. Use the human_approval tool when needed.",
        tools=restate_tools(human_approval),
    )

    session_service = RestateSessionService(ctx)
    await session_service.create_session(
        app_name=APP_NAME, user_id=user_id, session_id=ctx.key()
    )

    runner = RestateRunner(restate_context=ctx, agent=agent, app_name=APP_NAME, session_service=session_service)

    events = runner.run_async(
        user_id=user_id,
        session_id=ctx.key(),
        new_message=genai_types.Content(
            role="user",
            parts=[genai_types.Part.from_text(text=prompt.message)]
        )
    )

    final_response = ""
    async for event in events:
        if event.is_final_response() and event.content and event.content.parts:
            final_response = event.content.parts[0].text

    return final_response
