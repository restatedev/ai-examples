import restate
from pydantic_ai import Agent, RunContext
from restate.ext.pydantic import RestateAgent

from utils.models import InsuranceClaim

# <start_here>
medical_agent = Agent(
    "openai:gpt-4o-mini",
    system_prompt="Review medical claims for coverage and necessity. Approve/deny up to $50,000.",
)
restate_medical_agent = RestateAgent(medical_agent)

car_agent = Agent(
    "openai:gpt-4o-mini",
    system_prompt="Assess car claims for liability and damage. Approve/deny up to $25,000.",
)
restate_car_agent = RestateAgent(car_agent)

intake_agent = Agent(
    "openai:gpt-4o-mini",
    system_prompt="Route insurance claims to the appropriate specialist using the available tools.",
)


@intake_agent.tool
async def consult_medical_specialist(
    _run_ctx: RunContext[None], claim: InsuranceClaim
) -> str:
    """Route to the medical specialist for medical insurance claims."""
    result = await restate_medical_agent.run(claim.model_dump_json())
    return result.output


@intake_agent.tool
async def consult_car_specialist(
    _run_ctx: RunContext[None], claim: InsuranceClaim
) -> str:
    """Route to the car specialist for car insurance claims."""
    result = await restate_car_agent.run(claim.model_dump_json())
    return result.output


restate_intake_agent = RestateAgent(intake_agent)
agent_service = restate.Service("MultiAgentClaimApproval")


@agent_service.handler()
async def run(_ctx: restate.ObjectContext, claim: InsuranceClaim) -> str:
    result = await restate_intake_agent.run(f"Claim: {claim.model_dump_json()}")
    return result.output


# <end_here>


if __name__ == "__main__":
    import hypercorn
    import asyncio

    app = restate.app(services=[agent_service])
    conf = hypercorn.Config()
    conf.bind = ["0.0.0.0:9080"]
    asyncio.run(hypercorn.asyncio.serve(app, conf))
