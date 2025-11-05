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

class InsuranceClaim(BaseModel):
    claim_id: str
    claim_type: str
    amount: float
    description: str


# Simulate remote eligibility agent service
eligibility_agent_service = restate.Service("EligibilityAgent")

@eligibility_agent_service.handler()
async def run_eligibility_agent(ctx: restate.Context, claim: InsuranceClaim) -> str:
    """Analyze claim eligibility."""
    # Simulate eligibility check logic
    if claim.amount > 100000:
        return f"Claim {claim.claim_id} not eligible: Amount exceeds maximum coverage"
    elif claim.claim_type.lower() not in ["medical", "auto", "property"]:
        return f"Claim {claim.claim_id} not eligible: Invalid claim type"
    else:
        return f"Claim {claim.claim_id} is eligible for processing"


# Simulate remote fraud detection agent service
fraud_agent_service = restate.Service("FraudAgent")

@fraud_agent_service.handler()
async def run_fraud_agent(ctx: restate.Context, claim: InsuranceClaim) -> str:
    """Analyze the probability of fraud."""
    # Simulate fraud detection logic
    if claim.amount > 50000 and "accident" in claim.description.lower():
        return f"Claim {claim.claim_id} flagged: High amount with accident keywords - potential fraud risk"
    elif claim.description.lower().count("total loss") > 1:
        return f"Claim {claim.claim_id} flagged: Suspicious language patterns detected"
    else:
        return f"Claim {claim.claim_id} appears legitimate based on fraud analysis"


# Durable service call to the eligibility agent; persisted and retried by Restate
async def check_eligibility(tool_context: ToolContext, claim_id: str, claim_type: str, amount: float, description: str) -> str:
    """Analyze claim eligibility."""
    restate_context = tool_context.session.state["restate_context"]
    claim = InsuranceClaim(claim_id=claim_id, claim_type=claim_type, amount=amount, description=description)
    return await restate_context.service_call(run_eligibility_agent, claim)


# <start_here>
# Durable service call to the fraud agent; persisted and retried by Restate
async def check_fraud(tool_context: ToolContext, claim_id: str, claim_type: str, amount: float, description: str) -> str:
    """Analyze the probability of fraud."""
    restate_context = tool_context.session.state["restate_context"]
    claim = InsuranceClaim(claim_id=claim_id, claim_type=claim_type, amount=amount, description=description)
    return await restate_context.service_call(run_fraud_agent, claim)


agent_service = restate.VirtualObject("RemoteMultiAgentClaimApproval")


@agent_service.handler()
async def run(ctx: restate.ObjectContext, claim: InsuranceClaim) -> str:
    user_id = "user"

    claim_approval_coordinator = Agent(
        model=durable_model_calls(ctx, 'gemini-2.5-flash'),
        name='claim_approval_coordinator',
        description="Coordinates claim approval by analyzing eligibility and fraud risk.",
        instruction="You are a claim approval engine. Analyze the claim and use your tools to check eligibility and fraud risk, then decide whether to approve it.",
        tools=restate_tools(check_fraud, check_eligibility),
    )

    session_service = RestateSessionService(ctx)
    await session_service.create_session(
        app_name=APP_NAME, user_id=user_id, session_id=ctx.key()
    )

    runner = RestateRunner(restate_context=ctx, agent=claim_approval_coordinator, app_name=APP_NAME, session_service=session_service)

    events = runner.run_async(
        user_id=user_id,
        session_id=ctx.key(),
        new_message=genai_types.Content(
            role="user",
            parts=[genai_types.Part.from_text(text=f"Claim: {claim.model_dump_json()}")]
        )
    )

    final_response = ""
    async for event in events:
        if event.is_final_response() and event.content and event.content.parts:
            final_response = event.content.parts[0].text

    return final_response
# <end_here>