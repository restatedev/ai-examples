import restate

from google.adk import Runner
from google.adk.agents.llm_agent import Agent
from google.adk.apps import App
from google.genai.types import Content, Part
from restate.ext.adk import RestatePlugin, RestateSessionService, restate_context

from app.utils.models import InsuranceClaim
from app.utils.utils import run_eligibility_agent, run_fraud_agent

APP_NAME = "agents"


# Durable service call to the eligibility agent; persisted and retried by Restate
async def check_eligibility(claim: InsuranceClaim) -> str:
    """Analyze claim eligibility."""
    return await restate_context().service_call(run_eligibility_agent, claim)


# <start_here>
# Durable service call to the fraud agent; persisted and retried by Restate
async def check_fraud(claim: InsuranceClaim) -> str:
    """Analyze the probability of fraud."""
    return await restate_context().service_call(run_fraud_agent, claim)


agent = Agent(
    model="gemini-2.5-flash",
    name="ClaimApprovalCoordinator",
    instruction="You are a claim approval engine. Analyze the claim and use your tools to decide whether to approve it.",
    tools=[check_fraud, check_eligibility],
)

app = App(name=APP_NAME, root_agent=agent, plugins=[RestatePlugin()])
runner = Runner(app=app, session_service=RestateSessionService())

agent_service = restate.VirtualObject("RemoteMultiAgentClaimApproval")


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


# <end_here>
