import restate
from google.adk import Runner
from google.adk.agents.llm_agent import Agent
from google.adk.apps import App
from google.genai.types import Content, Part

from app.utils.models import InsuranceClaim
from app.utils.utils import (
    run_eligibility_agent,
    run_rate_comparison_agent,
    run_fraud_agent,
)

from middleware.restate_plugin import RestatePlugin
from middleware.restate_session_service import RestateSessionService
from middleware.restate_utils import restate_overrides

APP_NAME = "agents"

agent = Agent(
    model="gemini-2.0-flash",
    name="claim_decision_agent",
    description="Makes final claim approval decisions based on analysis results.",
    instruction="You are a claim decision engine. Analyze the provided assessments and make a final approval decision.",
)


app = App(name=APP_NAME, root_agent=agent, plugins=[RestatePlugin()])
session_service = RestateSessionService()

agent_service = restate.VirtualObject("ParallelAgentClaimApproval")


@agent_service.handler()
async def run(ctx: restate.ObjectContext, claim: InsuranceClaim) -> str:
    session_id = ctx.key()
    with restate_overrides(ctx):

        # Start multiple agents in parallel with auto retries and recovery
        eligibility = ctx.service_call(run_eligibility_agent, claim)
        cost = ctx.service_call(run_rate_comparison_agent, claim)
        fraud = ctx.service_call(run_fraud_agent, claim)

        # Wait for all responses
        await restate.gather(eligibility, cost, fraud)

        # Get the results
        eligibility_result = await eligibility
        cost_result = await cost
        fraud_result = await fraud

        # Run decision agent on outputs
        await session_service.create_session(
            app_name=APP_NAME, user_id=claim.user_id, session_id=session_id
        )
        runner = Runner(app=app, session_service=session_service)

        prompt = f"""Decide about claim: {claim.model_dump_json()}. 
        Base your decision on the following analyses: 
        Eligibility: {eligibility_result} Cost: {cost_result} Fraud: {fraud_result}"""
        events = runner.run_async(
            user_id=claim.user_id,
            session_id=ctx.key(),
            new_message=Content(role="user", parts=[Part.from_text(text=prompt)]),
        )
        final_response = ""
        async for event in events:
            if event.is_final_response() and event.content and event.content.parts:
                if event.content.parts[0].text:
                    final_response = event.content.parts[0].text
        return final_response
