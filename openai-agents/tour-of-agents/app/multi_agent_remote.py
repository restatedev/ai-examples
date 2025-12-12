import restate
from agents import Agent, Runner, function_tool
from restate.ext.openai import restate_context

from app.utils.utils import InsuranceClaim, run_eligibility_agent, run_fraud_agent


# Durable service call to the eligibility agent; persisted and retried by Restate
@function_tool
async def check_eligibility(claim: InsuranceClaim) -> str:
    """ "Analyze claim eligibility."""
    return await restate_context().service_call(run_eligibility_agent, claim)


# <start_here>
# Durable service call to the fraud agent; persisted and retried by Restate
@function_tool
async def check_fraud(claim: InsuranceClaim) -> str:
    """Analyze the probability of fraud."""
    return await restate_context().service_call(run_fraud_agent, claim)


claim_approval_coordinator = Agent(
    name="ClaimApprovalCoordinator",
    instructions="You are a claim approval engine. Analyze the claim and use your tools to decide whether to approve it.",
    tools=[check_eligibility, check_fraud],
)

agent_service = restate.Service("RemoteMultiAgentClaimApproval")


@agent_service.handler()
async def run(_ctx: restate.Context, claim: InsuranceClaim) -> str:
    result = await Runner.run(
        claim_approval_coordinator,
        input=f"Claim: {claim.model_dump_json()}",
    )
    return result.final_output


# <end_here>
