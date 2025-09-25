import restate
from agents import Agent, RunConfig, Runner

from app.utils.middleware import DurableModelCalls
from app.utils.utils import InsuranceClaim


eligibility_agent = Agent[restate.Context](
    name="EligibilityAgent",
    handoff_description="You are a helpful agent that analyzes insurance claim eligibility.",
    instructions="Decide whether the following claim is eligible for reimbursement." +
    "Respond with eligible if it's a medical claim, and not eligible otherwise.",
)

rate_comparison_agent = Agent[restate.Context](
    name="RateComparisonAgent",
    handoff_description="You are a helpful agent that analyzes whether the claim amount is reasonable.",
    instructions="Decide whether the cost of the claim is reasonable given the treatment." +
          "Respond with reasonable or not reasonable.",
)

fraud_agent = Agent[restate.Context](
    name="FraudCheckAgent",
    handoff_description="You are a helpful agent that analyzes the probability of insurance fraud.",
    instructions="Decide whether the claim is fraudulent." +
          "Always respond with low risk, medium risk, or high risk."
)


multi_agent_coordinator = Agent[restate.Context](
    name="MultiAgentClaimApproval",
    instructions="You are a claim approval engine. Analyze the claim and use your tools to decide whether to approve it.",
    tools=[
        eligibility_agent.as_tool(),
        rate_comparison_agent.as_tool(),
        fraud_agent.as_tool()
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