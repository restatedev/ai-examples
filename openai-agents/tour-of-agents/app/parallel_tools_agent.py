import restate

from agents import Agent, function_tool
from restate.ext.openai import restate_context, DurableRunner

from app.utils.utils import (
    InsuranceClaim,
    check_eligibility,
    compare_to_standard_rates,
    check_fraud,
)


# <start_here>
@function_tool
async def calculate_metrics(claim: InsuranceClaim) -> list[str]:
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


agent = Agent(
    name="ParallelToolsAgent",
    instructions="You are a claim analysis agent that analyzes insurance claims."
    "Use the calculate_metrics tool and decide whether to approve.",
    tools=[calculate_metrics],
)


agent_service = restate.Service("ParallelToolClaimAgent")


@agent_service.handler()
async def run(_ctx: restate.Context, claim: InsuranceClaim) -> str:
    result = await DurableRunner.run(agent, f"Claim: {claim.model_dump_json()}")
    return result.final_output
