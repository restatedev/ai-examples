"""Run several specialist agents in parallel, then feed their answers into
a decision agent."""

import restate
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model

from restate.ext.langchain import RestateMiddleware

from utils.models import InsuranceClaim
from utils.utils import (
    eligibility_agent_service,
    fraud_agent_service,
    rate_comparison_agent_service,
    run_eligibility_agent,
    run_fraud_agent,
    run_rate_comparison_agent,
)

# <start_here>
decision = create_agent(
    model=init_chat_model("openai:gpt-5.4"),
    system_prompt="You are a claim decision engine.",
    middleware=[RestateMiddleware()],
)


agent_service = restate.Service("ParallelAgentClaimApproval")


@agent_service.handler()
async def run(ctx: restate.Context, claim: InsuranceClaim) -> str:
    # Start multiple sub-agents in parallel with auto-retries and recovery.
    eligibility = ctx.service_call(run_eligibility_agent, claim)
    cost = ctx.service_call(run_rate_comparison_agent, claim)
    fraud = ctx.service_call(run_fraud_agent, claim)

    await restate.gather(eligibility, cost, fraud)

    result = await decision.ainvoke(
        {"messages": f"""Decide about claim: {claim.model_dump_json()}.
        Base your decision on the following analyses:
        Eligibility: {await eligibility} Cost {await cost} Fraud: {await fraud}"""}
    )
    return result["messages"][-1].content


# <end_here>


if __name__ == "__main__":
    import asyncio

    import hypercorn
    import hypercorn.asyncio

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
