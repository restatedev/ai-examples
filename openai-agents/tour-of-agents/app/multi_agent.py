import restate

from agents import Agent
from restate.ext.openai.runner_wrapper import RestateSession, DurableRunner

from app.utils.utils import InsuranceClaim


medical_agent = Agent(
    name="MedicalSpecialist",
    handoff_description="I handle medical insurance claims from intake to final decision.",
    instructions="Review medical claims for coverage and necessity. Approve/deny up to $50,000.",
)

car_agent = Agent(
    name="CarSpecialist",
    handoff_description="I handle car insurance claims from intake to final decision.",
    instructions="Assess car claims for liability and damage. Approve/deny up to $25,000.",
)


intake_agent = Agent(
    name="IntakeAgent",
    instructions="Route insurance claims to the appropriate specialist",
    handoffs = [medical_agent, car_agent]
)

agent_dict = {
    "IntakeAgent": intake_agent,
    "MedicalSpecialist": medical_agent,
    "AutoSpecialist": car_agent,
}

agent_service = restate.VirtualObject("MultiAgentClaimApproval")


@agent_service.handler()
async def run(ctx: restate.ObjectContext, claim: InsuranceClaim) -> str:
    # Store context in Restate's key-value store
    last_agent_name = await ctx.get("last_agent_name", type_hint=str) or "IntakeAgent"
    last_agent = agent_dict.get(last_agent_name, intake_agent)

    result = await DurableRunner.run(
        last_agent, f"Claim: {claim.model_dump_json()}", session=RestateSession()
    )

    ctx.set("last_agent_name", result.last_agent.name)
    return result.final_output
