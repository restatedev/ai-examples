import restate
from agents import Agent, RunConfig, Runner, ModelSettings, handoff, RunContextWrapper

from app.utils.middleware import DurableModelCalls, RestateSession
from app.utils.utils import InsuranceClaim

eligibility_agent = Agent[restate.Context](
    name="EligibilityAgent",
    handoff_description="You are a helpful agent that analyzes insurance claim eligibility.",
    instructions="Decide whether the following claim is eligible for reimbursement."
                 "Respond with eligible if it's a medical claim, and not eligible otherwise.",
)

fraud_agent = Agent[restate.Context](
    name="FraudCheckAgent",
    handoff_description="",
    instructions="You are a helpful agent that analyzes the probability of insurance fraud."
            "Decide whether the claim is fraudulent."
          "Always respond with low risk, medium risk, or high risk.",
)

claim_approval_coordinator = Agent[restate.Context](
    name="ClaimApprovalCoordinator",
    instructions="You are a claim approval engine. Analyze the claim and use your tools to decide whether to approve it.",
    # example of handoff usage
    handoffs=[eligibility_agent],
    # example of agent as tool usage
    tools=[fraud_agent.as_tool(tool_name="fraud check", tool_description="Check the fraud risk of the claim.")],
)

agent_dict = {
    "EligibilityAgent": eligibility_agent,
    "FraudCheckAgent": fraud_agent,
    "ClaimApprovalCoordinator": claim_approval_coordinator
}

agent_service = restate.VirtualObject("MultiAgentClaimApproval")

@agent_service.handler()
async def run(restate_context: restate.ObjectContext, claim: InsuranceClaim) -> str:

    # Store context in Restate's key-value store
    last_agent_name = await restate_context.get("last_agent_name", type_hint=str) or "ClaimApprovalCoordinator"
    last_agent = agent_dict.get(last_agent_name, claim_approval_coordinator)

    result = await Runner.run(
        last_agent,
        input=f"Claim: {claim.model_dump_json()}",
        context=restate_context,
        run_config=RunConfig(
            model="gpt-4o",
            model_provider=DurableModelCalls(restate_context),
            model_settings=ModelSettings(parallel_tool_calls=False)
        ),
        session=RestateSession(session_id=restate_context.key(), ctx=restate_context)
    )

    restate_context.set("last_agent_name", result.last_agent.name)

    return result.final_output