import restate
from agents import Agent, RunConfig, Runner, ModelSettings, handoff, RunContextWrapper, function_tool

from app.utils.middleware import DurableModelCalls, RestateSession
from app.utils.utils import InsuranceClaim

# Fraud check agent
# This can be deployed as a separate microservice
fraud_agent_service = restate.Service("FraudCheckAgent")

@fraud_agent_service.handler()
async def run_fraud_agent(restate_context: restate.Context, claim: InsuranceClaim) -> str:
    result = await Runner.run(
        Agent(
            name="FraudCheckAgent",
            instructions="You decide whether a claim is fraudulent."
                         "Always respond with low risk, medium risk, or high risk.",
        ),
        f"Claim: {claim.model_dump_json()}",
        run_config=RunConfig(model="gpt-4o", model_provider=DurableModelCalls(restate_context)),
    )
    return result.final_output


# <start_here>
# Claim approval coordinator agent
# This agent calls the remote fraud agent as a tool

# Durable service call to the fraud agent; persisted and retried by Restate
@function_tool()
async def check_fraud(wrapper: RunContextWrapper[restate.Context], claim: InsuranceClaim) -> str:
    """Calculate the probability of fraud."""
    restate_context = wrapper.context
    return await restate_context.service_call(run_fraud_agent, claim)


claim_approval_coordinator = Agent[restate.Context](
    name="ClaimApprovalCoordinator",
    instructions="You are a claim approval engine. Analyze the claim and use your tools to decide whether to approve it.",
    tools=[check_fraud],
)

agent_service = restate.VirtualObject("RemoteMultiAgentClaimApproval")


@agent_service.handler()
async def run(restate_context: restate.ObjectContext, claim: InsuranceClaim) -> str:
    result = await Runner.run(
        claim_approval_coordinator,
        input=f"Claim: {claim.model_dump_json()}",
        context=restate_context,
        run_config=RunConfig(
            model="gpt-4o",
            model_provider=DurableModelCalls(restate_context),
            model_settings=ModelSettings(parallel_tool_calls=False)
        ),
        session=RestateSession(session_id=restate_context.key(), ctx=restate_context)
    )
    return result.final_output
# <end_here>
