"""Remote agents over Restate RPC.

Each tool calls into a separate Restate service that runs its own LangChain
agent. Restate's `service_call` makes the inter-service hop durable: the
caller is journaled, the callee is journaled independently, and either side
can crash without losing progress."""

import restate
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain_core.tools import tool

from restate.ext.langchain import RestateMiddleware, restate_context

from utils.models import InsuranceClaim
from utils.utils import (
    eligibility_agent_service,
    fraud_agent_service,
    run_eligibility_agent,
    run_fraud_agent,
)


# Durable service call to the eligibility agent; persisted and retried by Restate.
@tool
async def check_eligibility(claim: InsuranceClaim) -> str:
    """Analyze claim eligibility."""
    return await restate_context().service_call(run_eligibility_agent, claim)


# <start_here>
# Durable service call to the fraud agent; persisted and retried by Restate.
@tool
async def check_fraud(claim: InsuranceClaim) -> str:
    """Analyze the probability of fraud."""
    return await restate_context().service_call(run_fraud_agent, claim)


agent = create_agent(
    model=init_chat_model("openai:gpt-4o-mini"),
    tools=[check_eligibility, check_fraud],
    system_prompt=(
        "You are a claim approval engine. Analyze the claim and use your "
        "tools to decide whether to approve it."
    ),
    middleware=[RestateMiddleware()],
)


agent_service = restate.Service("MultiAgentClaimApproval")


@agent_service.handler()
async def run(_ctx: restate.Context, claim: InsuranceClaim) -> str:
    result = await agent.ainvoke(
        {"messages": [{"role": "user", "content": f"Claim: {claim.model_dump_json()}"}]}
    )
    return result["messages"][-1].content


# <end_here>


if __name__ == "__main__":
    import asyncio

    import hypercorn
    import hypercorn.asyncio

    app = restate.app(
        services=[agent_service, fraud_agent_service, eligibility_agent_service]
    )
    conf = hypercorn.Config()
    conf.bind = ["0.0.0.0:9080"]
    asyncio.run(hypercorn.asyncio.serve(app, conf))
