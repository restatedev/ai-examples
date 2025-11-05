import restate
from google.adk.agents.llm_agent import Agent
from google.genai import types as genai_types
from pydantic import BaseModel

from middleware.middleware import durable_model_calls
from middleware.restate_runner import RestateRunner
from middleware.restate_session_service import RestateSessionService

APP_NAME = "agents"


class InsuranceClaim(BaseModel):
    claim_id: str
    claim_type: str
    amount: float
    description: str


# Simulate remote agent services for parallel execution
eligibility_agent_service = restate.Service("EligibilityAgent")


@eligibility_agent_service.handler()
async def run_eligibility_agent(ctx: restate.Context, claim: InsuranceClaim) -> str:
    """Analyze claim eligibility."""
    if claim.amount > 100000:
        return f"Claim {claim.claim_id} not eligible: Amount exceeds maximum coverage"
    elif claim.claim_type.lower() not in ["medical", "auto", "property"]:
        return f"Claim {claim.claim_id} not eligible: Invalid claim type"
    else:
        return f"Claim {claim.claim_id} is eligible for processing"


fraud_agent_service = restate.Service("FraudAgent")


@fraud_agent_service.handler()
async def run_fraud_agent(ctx: restate.Context, claim: InsuranceClaim) -> str:
    """Analyze the probability of fraud."""
    if claim.amount > 50000 and "accident" in claim.description.lower():
        return f"Claim {claim.claim_id} flagged: High amount with accident keywords - potential fraud risk"
    elif claim.description.lower().count("total loss") > 1:
        return f"Claim {claim.claim_id} flagged: Suspicious language patterns detected"
    else:
        return f"Claim {claim.claim_id} appears legitimate based on fraud analysis"


rate_comparison_agent_service = restate.Service("RateComparisonAgent")


@rate_comparison_agent_service.handler()
async def run_rate_comparison_agent(ctx: restate.Context, claim: InsuranceClaim) -> str:
    """Analyze cost and rate comparisons."""
    if claim.amount > 75000:
        return f"Claim {claim.claim_id} cost analysis: High-value claim, recommend additional review"
    elif claim.amount < 1000:
        return f"Claim {claim.claim_id} cost analysis: Low-value claim, fast-track processing"
    else:
        return f"Claim {claim.claim_id} cost analysis: Standard processing recommended"


agent_service = restate.VirtualObject("ParallelAgentClaimApproval")


# <start_here>
@agent_service.handler()
async def run(ctx: restate.ObjectContext, claim: InsuranceClaim) -> str:
    user_id = "user"

    # Start multiple agents in parallel with auto retries and recovery
    eligibility = ctx.service_call(run_eligibility_agent, claim)
    cost = ctx.service_call(run_rate_comparison_agent, claim)
    fraud = ctx.service_call(run_fraud_agent, claim)

    # Wait for all responses
    await restate.gather(eligibility, cost, fraud)

    # Get the results
    eligibility_result = await eligibility
    cost_result = await cost
    fraud_result = await fraud

    # Run decision agent on outputs
    decision_agent = Agent(
        model=durable_model_calls(ctx, "gemini-2.5-flash"),
        name="claim_decision_agent",
        description="Makes final claim approval decisions based on analysis results.",
        instruction="You are a claim decision engine. Analyze the provided assessments and make a final approval decision.",
    )

    session_service = RestateSessionService(ctx)
    await session_service.create_session(
        app_name=APP_NAME, user_id=user_id, session_id=ctx.key()
    )

    runner = RestateRunner(
        restate_context=ctx,
        agent=decision_agent,
        app_name=APP_NAME,
        session_service=session_service,
    )

    events = runner.run_async(
        user_id=user_id,
        session_id=ctx.key(),
        new_message=genai_types.Content(
            role="user",
            parts=[
                genai_types.Part.from_text(
                    text=f"Decide about claim: {claim.model_dump_json()}. "
                    "Base your decision on the following analyses: "
                    f"Eligibility: {eligibility_result} Cost: {cost_result} Fraud: {fraud_result}"
                )
            ],
        ),
    )

    final_response = ""
    async for event in events:
        if event.is_final_response() and event.content and event.content.parts:
            final_response = event.content.parts[0].text

    return final_response


# <end_here>
