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
review_agent = Agent(
    model="gemini-2.5-flash",
    name="medical_specialist",
    description="Reviews medical insurance claims for coverage and necessity.",
    instruction="""You are a medical specialist. Review medical claims for coverage and necessity. 
    You can approve/deny claims up to $50,000. Make a final decision on this claim.""",
)

car_agent = Agent(
    model="gemini-2.5-flash",
    name="auto_specialist",
    description="Assesses auto insurance claims for liability and damage.",
    instruction="""You are an auto specialist. Assess auto claims for liability and damage. 
    You can approve/deny claims up to $25,000. Make a final decision on this claim.""",
)

property_agent = Agent(
    model="gemini-2.5-flash",
    name="property_specialist",
    description="Evaluates property insurance claims for damage and coverage.",
    instruction="""You are a property specialist. Evaluate property claims for damage and coverage. 
    Make a final decision on this claim.""",
)

agent = Agent(
    model="gemini-2.5-flash",
    name="intake_agent",
    description="Routes insurance claims to appropriate specialists.",
    instruction=f"""You are an intake agent. Analyze the claim and determine if it should go to a specialist.""",
    sub_agents=[property_agent, car_agent, review_agent],
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
