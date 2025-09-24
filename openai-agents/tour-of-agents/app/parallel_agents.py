import restate
from agents import Agent, RunConfig, Runner, function_tool, RunContextWrapper

from app.utils.middleware import DurableModelCalls
from app.utils.utils import (
    InsuranceClaim,
    check_eligibility,
    compare_to_standard_rates,
    check_fraud
)


@function_tool
async def analyze_eligibility(
    wrapper: RunContextWrapper[restate.Context], claim: InsuranceClaim
) -> str:
    """Analyze claim eligibility using durable execution."""
    restate_context = wrapper.context
    return await restate_context.run_typed("eligibility_analysis", check_eligibility, claim=claim)


@function_tool
async def analyze_cost(
    wrapper: RunContextWrapper[restate.Context], claim: InsuranceClaim
) -> str:
    """Analyze claim cost comparison using durable execution."""
    restate_context = wrapper.context
    return await restate_context.run_typed("cost_analysis", compare_to_standard_rates, claim=claim)


@function_tool
async def analyze_fraud(
    wrapper: RunContextWrapper[restate.Context], claim: InsuranceClaim
) -> str:
    """Analyze claim fraud risk using durable execution."""
    restate_context = wrapper.context
    return await restate_context.run_typed("fraud_analysis", check_fraud, claim=claim)


parallel_agents_coordinator = Agent[restate.Context](
    name="ParallelAgentCoordinator",
    instructions="You are a claim coordinator agent that uses multiple specialized analysis tools to evaluate insurance claims. Use all tools to get comprehensive analysis before making a decision.",
    tools=[analyze_eligibility, analyze_cost, analyze_fraud],
)


agent_service = restate.Service("ParallelAgentClaimApproval")


@agent_service.handler()
async def run(restate_context: restate.Context, claim: InsuranceClaim) -> str:
    result = await Runner.run(
        parallel_agents_coordinator,
        input=f"Analyze this insurance claim comprehensively: {claim.model_dump_json()}. Use all available tools to evaluate eligibility, cost, and fraud risk before making your final decision.",
        context=restate_context,
        run_config=RunConfig(
            model="gpt-4o", model_provider=DurableModelCalls(restate_context)
        ),
    )

    return result.final_output