import restate
from agents import Agent, RunConfig, Runner, function_tool, RunContextWrapper

from app.utils.middleware import DurableModelCalls
from app.utils.utils import (
    InsuranceClaim,
    check_eligibility,
    check_fraud,
)


@function_tool
async def analyze_eligibility(
    wrapper: RunContextWrapper[restate.Context], claim: InsuranceClaim
) -> str:
    """Analyze eligibility result using durable execution."""
    restate_context = wrapper.context
    return await restate_context.run_typed("Eligibility analysis", check_eligibility, claim=claim)


@function_tool
async def analyze_fraud(
    wrapper: RunContextWrapper[restate.Context], claim: InsuranceClaim
) -> str:
    """Analyze probability of fraud using durable execution."""
    restate_context = wrapper.context
    return await restate_context.run_typed("Fraud analysis", check_fraud, claim=claim)


multi_agent_coordinator = Agent[restate.Context](
    name="MultiAgentClaimApproval",
    instructions="You are a claim approval engine. Analyze the claim and use your tools to decide whether to approve it.",
    tools=[analyze_eligibility, analyze_fraud],
)


agent_service = restate.Service("MultiAgentClaimApproval")


@agent_service.handler()
async def run(restate_context: restate.Context, claim: InsuranceClaim) -> str:
    result = await Runner.run(
        multi_agent_coordinator,
        input=f"Claim: {claim.model_dump_json()}",
        context=restate_context,
        run_config=RunConfig(
            model="gpt-4o", model_provider=DurableModelCalls(restate_context)
        ),
    )

    return result.final_output