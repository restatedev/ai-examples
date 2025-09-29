import restate
from agents import Agent, RunConfig, Runner, ModelSettings, handoff, RunContextWrapper

from app.utils.middleware import DurableModelCalls, RestateSession
from app.utils.utils import InsuranceClaim

intake_agent = Agent[restate.ObjectContext](
    name="IntakeAgent",
    instructions="Route insurance claims to the appropriate specialist: medical, auto, or property.",
)

medical_specialist = Agent[restate.ObjectContext](
    name="MedicalSpecialist",
    handoff_description="I handle medical insurance claims from intake to final decision.",
    instructions="Review medical claims for coverage and necessity. Approve/deny up to $50,000.",
)

auto_specialist = Agent[restate.ObjectContext](
    name="AutoSpecialist",
    handoff_description="I handle auto insurance claims from intake to final decision.",
    instructions="Assess auto claims for liability and damage. Approve/deny up to $25,000.",
)

property_specialist = Agent[restate.ObjectContext](
    name="PropertySpecialist",
    handoff_description="I handle property insurance claims from intake to final decision.",
    instructions="Evaluate property damage claims and coverage. Approve/deny up to $100,000.",
)

# Configure handoffs so intake agent can route to specialists
intake_agent.handoffs = [medical_specialist, auto_specialist, property_specialist]

agent_dict = {
    "IntakeAgent": intake_agent,
    "MedicalSpecialist": medical_specialist,
    "AutoSpecialist": auto_specialist,
    "PropertySpecialist": property_specialist,
}

agent_service = restate.VirtualObject("MultiAgentClaimApproval")


@agent_service.handler()
async def run(restate_context: restate.ObjectContext, claim: InsuranceClaim) -> str:

    # Store context in Restate's key-value store
    last_agent_name = (
        await restate_context.get("last_agent_name", type_hint=str)
        or "IntakeAgent"
    )
    last_agent = agent_dict.get(last_agent_name, intake_agent)

    restate_session = await RestateSession.create(session_id=restate_context.key(), ctx=restate_context)
    result = await Runner.run(
        last_agent,
        input=f"Claim: {claim.model_dump_json()}",
        context=restate_context,
        run_config=RunConfig(
            model="gpt-4o",
            model_provider=DurableModelCalls(restate_context),
            model_settings=ModelSettings(parallel_tool_calls=False),
        ),
        session=restate_session,
    )

    restate_context.set("last_agent_name", result.last_agent.name)

    return result.final_output
