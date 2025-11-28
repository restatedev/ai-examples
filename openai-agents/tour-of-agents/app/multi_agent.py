import restate
from agents import Agent

from app.utils.middleware import Runner, RestateSession
from app.utils.utils import InsuranceClaim

intake_agent = Agent(
    name="IntakeAgent",
    instructions="Route insurance claims to the appropriate specialist: medical, auto, or property.",
)

medical_specialist = Agent(
    name="MedicalSpecialist",
    handoff_description="I handle medical insurance claims from intake to final decision.",
    instructions="Review medical claims for coverage and necessity. Approve/deny up to $50,000.",
)

auto_specialist = Agent(
    name="AutoSpecialist",
    handoff_description="I handle auto insurance claims from intake to final decision.",
    instructions="Assess auto claims for liability and damage. Approve/deny up to $25,000.",
)

# Configure handoffs so intake agent can route to specialists
intake_agent.handoffs = [medical_specialist, auto_specialist]

agent_dict = {
    "IntakeAgent": intake_agent,
    "MedicalSpecialist": medical_specialist,
    "AutoSpecialist": auto_specialist,
}

agent_service = restate.VirtualObject("MultiAgentClaimApproval")


@agent_service.handler()
async def run(restate_context: restate.ObjectContext, claim: InsuranceClaim) -> str:

    # Store context in Restate's key-value store
    last_agent_name = (
        await restate_context.get("last_agent_name", type_hint=str) or "IntakeAgent"
    )
    last_agent = agent_dict.get(last_agent_name, intake_agent)

    result = await Runner.run(
        last_agent,
        input=f"Claim: {claim.model_dump_json()}",
        session=RestateSession(),
    )

    restate_context.set("last_agent_name", result.last_agent.name)

    return result.final_output
