import restate
from agents import Agent, RunConfig, Runner, ModelSettings

from app.utils.middleware import DurableModelCalls
from app.utils.utils import InsuranceClaim

agent_service = restate.Service("ParallelAgentClaimApproval")


# <start_here>
@agent_service.handler()
async def run(restate_context: restate.Context, claim: InsuranceClaim) -> str:

    # Start multiple agents in parallel with auto retries and recovery
    eligibility = restate_context.service_call(run_eligibility_agent, claim)
    fraud = restate_context.service_call(run_fraud_agent, claim)

    # Wait for all responses
    await restate.gather(eligibility, fraud)

    # Run decision agent on outputs
    result = await Runner.run(
        Agent(
            name="ClaimApprovalAgent", instructions="You are a claim decision engine."
        ),
        input=f"Decide about claim: {claim.model_dump_json()}. "
        "Base your decision on the following analyses:"
        f"Eligibility: {await eligibility} Fraud: {await fraud}",
        run_config=RunConfig(
            model="gpt-4o",
            model_provider=DurableModelCalls(restate_context),
            model_settings=ModelSettings(parallel_tool_calls=False),
        ),
    )
    return result.final_output


# <end_here>


@agent_service.handler()
async def run_eligibility_agent(
    restate_context: restate.Context, claim: InsuranceClaim
) -> str:
    result = await Runner.run(
        Agent(
            name="EligibilityAgent",
            instructions="Decide whether the following claim is eligible for reimbursement."
            "Respond with eligible if it's a medical claim, and not eligible otherwise.",
        ),
        input=claim.model_dump_json(),
        run_config=RunConfig(
            model="gpt-4o",
            model_provider=DurableModelCalls(restate_context),
            model_settings=ModelSettings(parallel_tool_calls=False),
        ),
    )
    return result.final_output


@agent_service.handler()
async def run_fraud_agent(
    restate_context: restate.Context, claim: InsuranceClaim
) -> str:
    result = await Runner.run(
        Agent(
            name="FraudAgent",
            instructions="Decide whether the cost of the claim is reasonable given the treatment."
            "Respond with reasonable or not reasonable.",
        ),
        input=claim.model_dump_json(),
        run_config=RunConfig(
            model="gpt-4o",
            model_provider=DurableModelCalls(restate_context),
            model_settings=ModelSettings(parallel_tool_calls=False),
        ),
    )
    return result.final_output
