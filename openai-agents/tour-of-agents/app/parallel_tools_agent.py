import restate
from agents import (
    Agent,
    RunConfig,
    Runner,
    function_tool,
    RunContextWrapper,
    ModelSettings,
)

from app.utils.middleware import DurableModelCalls, raise_restate_errors
from app.utils.utils import (
    InsuranceClaim,
    check_eligibility,
    compare_to_standard_rates,
    check_fraud,
)


# <start_here>
@function_tool(failure_error_function=raise_restate_errors)
async def calculate_metrics(
    wrapper: RunContextWrapper[restate.Context], claim: InsuranceClaim
) -> list[str]:
    """Calculate claim metrics."""
    restate_context = wrapper.context

    # Run tools/steps in parallel with durable execution
    results_done = await restate.gather(
        restate_context.run_typed("eligibility", check_eligibility, claim=claim),
        restate_context.run_typed("cost", compare_to_standard_rates, claim=claim),
        restate_context.run_typed("fraud", check_fraud, claim=claim),
    )
    return [await result for result in results_done]


# <end_here>


parallel_tools_agent = Agent[restate.Context](
    name="ParallelToolsAgent",
    instructions="You are a claim analysis agent that analyzes insurance claims.",
    tools=[calculate_metrics],
)


agent_service = restate.Service("ParallelToolClaimAgent")


@agent_service.handler()
async def run(restate_context: restate.Context, claim: InsuranceClaim) -> str:
    result = await Runner.run(
        parallel_tools_agent,
        input=f"Analyze the claim {claim.model_dump_json()}." 
              "Use your tools to calculate key metrics and decide whether to approve.",
        context=restate_context,
        run_config=RunConfig(
            model="gpt-4o",
            model_provider=DurableModelCalls(restate_context),
            model_settings=ModelSettings(parallel_tool_calls=False),
        ),
    )
    return result.final_output
