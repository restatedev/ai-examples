import restate
from pydantic_ai import Agent
from restate.ext.pydantic import RestateAgent

from utils.models import InsuranceClaim
from utils.utils import (
    run_eligibility_agent,
    run_fraud_agent,
    run_rate_comparison_agent,
    fraud_agent_service,
    rate_comparison_agent_service,
    eligibility_agent_service,
)

decision_agent = Agent(
    "openai:gpt-4o-mini",
    system_prompt="You are a claim decision engine.",
)
restate_decision_agent = RestateAgent(decision_agent)

agent_service = restate.Service("ParallelAgentClaimApproval")


# <start_here>
@agent_service.handler()
async def run(ctx: restate.Context, claim: InsuranceClaim) -> str:
    # Start multiple agents in parallel with auto retries and recovery
    eligibility = ctx.service_call(run_eligibility_agent, claim)
    cost = ctx.service_call(run_rate_comparison_agent, claim)
    fraud = ctx.service_call(run_fraud_agent, claim)

    # Wait for all responses
    await restate.gather(eligibility, cost, fraud)

    # Run decision agent on outputs
    result = await restate_decision_agent.run(
        f"Decide about claim: {claim.model_dump_json()}. "
        "Base your decision on the following analyses:"
        f"Eligibility: {await eligibility} Cost {await cost} Fraud: {await fraud}",
    )
    return result.output


# <end_here>


if __name__ == "__main__":
    import hypercorn
    import asyncio

    app = restate.app(
        services=[
            agent_service,
            fraud_agent_service,
            rate_comparison_agent_service,
            eligibility_agent_service,
        ]
    )
    conf = hypercorn.Config()
    conf.bind = ["0.0.0.0:9080"]
    asyncio.run(hypercorn.asyncio.serve(app, conf))
