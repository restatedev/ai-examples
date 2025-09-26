import restate
from agents import Agent, RunConfig, Runner, ModelSettings

from app.utils.middleware import DurableModelCalls
from app.utils.utils import InsuranceClaim

# Eligibility agent

eligibility_agent = Agent[restate.Context](
    name="EligibilityAgent",
    handoff_description="You are a helpful agent that analyzes insurance claim eligibility.",
    instructions="Decide whether the following claim is eligible for reimbursement." +
                 "Respond with eligible if it's a medical claim, and not eligible otherwise.",
)

eligibility_agent_service = restate.Service("EligibilityAgent")

@eligibility_agent_service.handler()
async def run(restate_context: restate.Context, claim: InsuranceClaim) -> str:
    result = await Runner.run(
        eligibility_agent,
        input=f"Claim: {claim.model_dump_json()}",
        context=restate_context,
        run_config=RunConfig(
            model="gpt-4o", model_provider=DurableModelCalls(restate_context)
        ),
    )

    return result.final_output

# Fraud check agent
fraud_agent = Agent[restate.Context](
    name="FraudCheckAgent",
    handoff_description="",
    instructions="You are a helpful agent that analyzes the probability of insurance fraud."
            "Decide whether the claim is fraudulent."
          "Always respond with low risk, medium risk, or high risk.",
)

fraud_agent_service = restate.Service("FraudCheckAgent")

@fraud_agent_service.handler()
async def run(restate_context: restate.Context, claim: InsuranceClaim) -> str:
    result = await Runner.run(
        eligibility_agent,
        input=f"Claim: {claim.model_dump_json()}",
        context=restate_context,
        run_config=RunConfig(
            model="gpt-4o",
            model_provider=DurableModelCalls(restate_context, max_retries=3),
            model_settings=ModelSettings(parallel_tool_calls=False)
        ),
    )

    return result.final_output

multi_agent_coordinator = Agent[restate.Context](
    name="MultiAgentClaimApproval",
    instructions="You are a claim approval engine. Analyze the claim and use your tools to decide whether to approve it.",
    handoffs=[
        eligibility_agent,
        fraud_agent
    ]
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