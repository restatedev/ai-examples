import restate
from google.adk.agents.llm_agent import Agent
from google.genai import types as genai_types

from app.utils.models import InsuranceClaim
from app.utils.utils import (
    run_eligibility_agent,
    run_rate_comparison_agent,
    run_fraud_agent,
)
from middleware.middleware import durable_model_calls
from middleware.restate_runner import create_restate_runner

APP_NAME = "agents"


agent_service = restate.VirtualObject("ParallelAgentClaimApproval")


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

    runner = await create_restate_runner(ctx, APP_NAME, user_id, decision_agent)
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
