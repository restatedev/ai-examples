import restate
from agents import (
    Agent,
    RunConfig,
    Runner,
    ModelSettings,
    RunContextWrapper,
    function_tool,
)

from app.utils.middleware import DurableModelCalls, raise_restate_errors
from app.utils.utils import InsuranceClaim, run_eligibility_agent, run_fraud_agent


# Durable service call to the eligibility agent; persisted and retried by Restate
@function_tool(failure_error_function=raise_restate_errors)
async def check_eligibility(
    wrapper: RunContextWrapper[restate.Context], claim: InsuranceClaim
) -> str:
    """ "Analyze claim eligibility."""
    restate_context = wrapper.context
    return await restate_context.service_call(run_eligibility_agent, claim)


# <start_here>
# Durable service call to the fraud agent; persisted and retried by Restate
@function_tool(failure_error_function=raise_restate_errors)
async def check_fraud(
    wrapper: RunContextWrapper[restate.Context], claim: InsuranceClaim
) -> str:
    """Analyze the probability of fraud."""
    restate_context = wrapper.context
    return await restate_context.service_call(run_fraud_agent, claim)


claim_approval_coordinator = Agent[restate.Context](
    name="ClaimApprovalCoordinator",
    instructions="You are a claim approval engine. Analyze the claim and use your tools to decide whether to approve it.",
    tools=[check_fraud, check_eligibility],
)

agent_service = restate.Service("RemoteMultiAgentClaimApproval")


@agent_service.handler()
async def run(restate_context: restate.Context, claim: InsuranceClaim) -> str:
    result = await Runner.run(
        claim_approval_coordinator,
        input=f"Claim: {claim.model_dump_json()}",
        context=restate_context,
        run_config=RunConfig(
            model="gpt-4o",
            model_provider=DurableModelCalls(restate_context),
            model_settings=ModelSettings(parallel_tool_calls=False),
        ),
    )
    return result.final_output


# <end_here>