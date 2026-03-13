import restate
from pydantic_ai import Agent, RunContext
from restate.ext.pydantic import RestateAgent, restate_context

from utils.models import InsuranceClaim
from utils.utils import (
    check_eligibility,
    compare_to_standard_rates,
    check_fraud,
)

agent = Agent(
    "openai:gpt-4o-mini",
    system_prompt="You are a claim analysis agent that analyzes insurance claims."
    "Use the calculate_metrics tool and decide whether to approve.",
)


# <start_here>
@agent.tool
async def calculate_metrics(
    _run_ctx: RunContext[None], claim: InsuranceClaim
) -> list[str]:
    """Calculate claim metrics."""
    ctx = restate_context()

    # Run tools/steps in parallel with durable execution
    results_done = await restate.gather(
        ctx.run_typed("eligibility", check_eligibility, claim=claim),
        ctx.run_typed("cost", compare_to_standard_rates, claim=claim),
        ctx.run_typed("fraud", check_fraud, claim=claim),
    )
    return [await result for result in results_done]


# <end_here>

restate_agent = RestateAgent(agent)

agent_service = restate.Service("ParallelToolClaimAgent")


@agent_service.handler()
async def run(_ctx: restate.Context, claim: InsuranceClaim) -> str:
    result = await restate_agent.run(f"Claim: {claim.model_dump_json()}")
    return result.output


if __name__ == "__main__":
    import hypercorn
    import asyncio

    app = restate.app(services=[agent_service])
    conf = hypercorn.Config()
    conf.bind = ["0.0.0.0:9080"]
    asyncio.run(hypercorn.asyncio.serve(app, conf))
