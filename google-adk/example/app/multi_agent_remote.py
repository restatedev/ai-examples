import restate
from google.adk.agents.llm_agent import Agent
from google.adk.tools.tool_context import ToolContext
from google.genai import types as genai_types
from pydantic import BaseModel

from app.utils.models import InsuranceClaim
from app.utils.utils import run_fraud_agent, run_eligibility_agent
from middleware.middleware import durable_model_calls
from middleware.restate_runner import RestateRunner
from middleware.restate_session_service import RestateSessionService
from middleware.restate_tools import restate_tools

APP_NAME = "agents"


# Durable service call to the eligibility agent; persisted and retried by Restate
async def check_eligibility(tool_context: ToolContext, claim: InsuranceClaim) -> str:
    """Analyze claim eligibility."""
    restate_context = tool_context.session.state["restate_context"]
    return await restate_context.object_call(
        run_eligibility_agent, tool_context.session.id, claim
    )


# <start_here>
# Durable service call to the fraud agent; persisted and retried by Restate
async def check_fraud(tool_context: ToolContext, claim: InsuranceClaim) -> str:
    """Analyze the probability of fraud."""
    restate_context = tool_context.session.state["restate_context"]
    return await restate_context.object_call(
        run_fraud_agent, tool_context.session.id, claim
    )


agent_service = restate.VirtualObject("RemoteMultiAgentClaimApproval")


@agent_service.handler()
async def run(ctx: restate.ObjectContext, claim: InsuranceClaim) -> str:
    user_id = "user"

    claim_approval_coordinator = Agent(
        model=durable_model_calls(ctx, "gemini-2.5-flash"),
        name="claim_approval_coordinator",
        description="Coordinates claim approval by analyzing eligibility and fraud risk.",
        instruction="You are a claim approval engine. Analyze the claim and use your tools to check eligibility and fraud risk, then decide whether to approve it.",
        tools=restate_tools(check_fraud, check_eligibility),
    )

    session_service = RestateSessionService(ctx)
    await session_service.create_session(
        app_name=APP_NAME, user_id=user_id, session_id=ctx.key()
    )

    runner = RestateRunner(
        restate_context=ctx,
        agent=claim_approval_coordinator,
        app_name=APP_NAME,
        session_service=session_service,
    )

    events = runner.run_async(
        user_id=user_id,
        session_id=ctx.key(),
        new_message=genai_types.Content(
            role="user",
            parts=[
                genai_types.Part.from_text(text=f"Claim: {claim.model_dump_json()}")
            ],
        ),
    )

    final_response = ""
    async for event in events:
        if event.is_final_response() and event.content and event.content.parts:
            final_response = event.content.parts[0].text

    return final_response


# <end_here>
