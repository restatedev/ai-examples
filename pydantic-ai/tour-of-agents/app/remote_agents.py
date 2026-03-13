import restate
from pydantic_ai import Agent, RunContext
from restate.ext.pydantic import RestateAgent, restate_context

from utils.models import InsuranceClaim
from utils.utils import run_eligibility_agent, run_fraud_agent

agent = Agent(
    "openai:gpt-4o-mini",
    system_prompt="You are a claim approval engine. Analyze the claim and use your tools to decide whether to approve it.",
)


# Durable service call to the eligibility agent; persisted and retried by Restate
@agent.tool
async def check_eligibility(_run_ctx: RunContext[None], claim: InsuranceClaim) -> str:
    """Analyze claim eligibility."""
    return await restate_context().service_call(run_eligibility_agent, claim)


# <start_here>
# Durable service call to the fraud agent; persisted and retried by Restate
@agent.tool
async def check_fraud(_run_ctx: RunContext[None], claim: InsuranceClaim) -> str:
    """Analyze the probability of fraud."""
    return await restate_context().service_call(run_fraud_agent, claim)


restate_agent = RestateAgent(agent)

agent_service = restate.Service("MultiAgentClaimApproval")


@agent_service.handler()
async def run(_ctx: restate.Context, claim: InsuranceClaim) -> str:
    result = await restate_agent.run(f"Claim: {claim.model_dump_json()}")
    return result.output


# <end_here>


if __name__ == "__main__":
    import hypercorn
    import asyncio

    from utils.utils import fraud_agent_service, eligibility_agent_service

    app = restate.app(
        services=[agent_service, fraud_agent_service, eligibility_agent_service]
    )
    conf = hypercorn.Config()
    conf.bind = ["0.0.0.0:9080"]
    asyncio.run(hypercorn.asyncio.serve(app, conf))
