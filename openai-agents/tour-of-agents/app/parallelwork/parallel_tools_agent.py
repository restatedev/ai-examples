import restate
from agents import Agent, RunConfig, Runner, function_tool, RunContextWrapper

from app.middleware import DurableModelCalls
from app.utils import (
    InsuranceClaim,
    check_eligibility,
    compare_to_standard_rates,
    check_fraud
)


@function_tool
async def calculate_metrics(
    wrapper: RunContextWrapper[restate.Context], claim: InsuranceClaim
) -> dict:
    """Calculate all claim metrics in parallel."""
    restate_context = wrapper.context

    # Execute each calculation as a separate durable step
    eligibility_result = await restate_context.run_typed(
        "eligibility",
        check_eligibility,
        claim=claim
    )

    cost_result = await restate_context.run_typed(
        "cost",
        compare_to_standard_rates,
        claim=claim
    )

    fraud_result = await restate_context.run_typed(
        "fraud",
        check_fraud,
        claim=claim
    )

    return {
        "eligibility": eligibility_result,
        "cost": cost_result,
        "fraud": fraud_result,
        "processed_at": "parallel"
    }


parallel_tools_agent = Agent[restate.Context](
    name="ParallelToolsAgent",
    instructions="You are a claim analysis agent that uses parallel tools to analyze insurance claims efficiently.",
    tools=[calculate_metrics],
)


agent_service = restate.Service("ParallelToolClaimAgent")


@agent_service.handler()
async def run(restate_context: restate.Context, claim: InsuranceClaim) -> str:
    result = await Runner.run(
        parallel_tools_agent,
        input=f"Analyze the claim {claim.model_dump_json()}. Use your tools to calculate key metrics and decide whether to approve.",
        context=restate_context,
        run_config=RunConfig(
            model="gpt-4o", model_provider=DurableModelCalls(restate_context)
        ),
    )

    return result.final_output