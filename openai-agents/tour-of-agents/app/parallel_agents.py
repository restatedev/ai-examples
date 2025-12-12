import restate
from agents import Agent, Runner
from restate.ext.openai import DurableOpenAIAgents

from app.utils.utils import (
    InsuranceClaim,
    run_eligibility_agent,
    run_fraud_agent,
    run_rate_comparison_agent,
)

agent_service = restate.Service(
    "ParallelAgentClaimApproval", invocation_context_managers=[DurableOpenAIAgents]
)


# <start_here>
@agent_service.handler()
async def run(restate_context: restate.Context, claim: InsuranceClaim) -> str:

    # Start multiple agents in parallel with auto retries and recovery
    eligibility = restate_context.service_call(run_eligibility_agent, claim)
    cost = restate_context.service_call(run_rate_comparison_agent, claim)
    fraud = restate_context.service_call(run_fraud_agent, claim)

    # Wait for all responses
    await restate.gather(eligibility, cost, fraud)

    # Run decision agent on outputs
    result = await Runner.run(
        Agent(
            name="ClaimApprovalAgent", instructions="You are a claim decision engine."
        ),
        input=f"Decide about claim: {claim.model_dump_json()}. "
        "Base your decision on the following analyses:"
        f"Eligibility: {await eligibility} Cost {await cost} Fraud: {await fraud}",
    )
    return result.final_output


# <end_here>
