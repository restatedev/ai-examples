import restate
from google.adk import Runner
from google.adk.agents.llm_agent import Agent
from google.adk.apps import App
from google.genai.types import Content, Part

from app.utils.models import InsuranceClaim

from middleware.restate_plugin import RestatePlugin
from middleware.restate_session_service import RestateSessionService
from middleware.restate_utils import restate_overrides

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
session_service = RestateSessionService()

agent_service = restate.VirtualObject("MultiAgentClaimApproval")


@agent_service.handler()
async def run(ctx: restate.ObjectContext, claim: InsuranceClaim) -> str:
    session_id = ctx.key()
    with restate_overrides(ctx):
        await session_service.create_session(
            app_name=APP_NAME, user_id=claim.user_id, session_id=session_id
        )

        runner = Runner(app=app, session_service=session_service)
        events = runner.run_async(
            user_id=claim.user_id,
            session_id=ctx.key(),
            new_message=Content(
                role="user",
                parts=[Part.from_text(text=f"Claim: {claim.model_dump_json()}")],
            ),
        )
        final_response = ""
        async for event in events:
            if event.is_final_response() and event.content and event.content.parts:
                final_response = event.content.parts[0].text

        return final_response
