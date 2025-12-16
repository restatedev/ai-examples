import restate

from google.adk import Runner
from google.adk.agents.llm_agent import Agent
from google.adk.apps import App
from google.genai.types import Content, Part
from restate.ext.adk import RestatePlugin, RestateSessionService

from app.utils.models import InsuranceClaim

APP_NAME = "agents"

# AGENTS
# Determine which specialist to use based on claim type
medical_agent = Agent(
    model="gemini-2.5-flash",
    name="medical_specialist",
    description="Reviews medical insurance claims for coverage and necessity.",
    instruction="Review medical claims for coverage and necessity. Approve/deny up to $50,000.",
)

car_agent = Agent(
    model="gemini-2.5-flash",
    name="car_specialist",
    description="Assesses car insurance claims for liability and damage.",
    instruction="Assess car claims for liability and damage. Approve/deny up to $25,000.",
)

agent = Agent(
    model="gemini-2.5-flash",
    name="intake_agent",
    instruction="Route insurance claims to the appropriate specialist",
    sub_agents=[car_agent, medical_agent],
)

# Enables retries and recovery for model calls and tool executions
app = App(name=APP_NAME, root_agent=agent, plugins=[RestatePlugin()])
runner = Runner(app=app, session_service=RestateSessionService())

agent_service = restate.VirtualObject("MultiAgentClaimApproval")


@agent_service.handler()
async def run(ctx: restate.ObjectContext, claim: InsuranceClaim) -> str | None:
    events = runner.run_async(
        user_id=ctx.key(),
        session_id=claim.session_id,
        new_message=Content(
            role="user",
            parts=[Part.from_text(text=f"Claim: {claim.model_dump_json()}")],
        ),
    )

    final_response = None
    async for event in events:
        if event.is_final_response() and event.content and event.content.parts:
            if event.content.parts[0].text:
                final_response = event.content.parts[0].text
    return final_response
