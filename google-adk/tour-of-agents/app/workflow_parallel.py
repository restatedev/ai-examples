import restate

from google.adk import Runner
from google.adk.agents.llm_agent import Agent
from google.adk.apps import App
from google.genai.types import Content, Part
from restate.ext.adk import RestateSessionService, RestatePlugin

from utils.models import InsuranceClaim
from utils.utils import (
    run_eligibility_agent,
    run_rate_comparison_agent,
    run_fraud_agent,
    parse_agent_response,
)

APP_NAME = "agents"

agent = Agent(
    model="gemini-2.5-flash",
    name="claim_decision_agent",
    instruction="You are a claim decision engine. Analyze the provided assessments and make a final approval decision.",
)


app = App(name=APP_NAME, root_agent=agent, plugins=[RestatePlugin()])
runner = Runner(app=app, session_service=RestateSessionService())

agent_service = restate.VirtualObject("ParallelAgentClaimApproval")


# <start_here>
@agent_service.handler()
async def run(ctx: restate.ObjectContext, claim: InsuranceClaim) -> str | None:

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
    prompt = f"""Decide about claim: {claim.model_dump_json()}. Assessments:
    Eligibility: {eligibility_result} Cost: {cost_result} Fraud: {fraud_result}"""

    events = runner.run_async(
        user_id=ctx.key(),
        session_id=claim.session_id,
        new_message=Content(role="user", parts=[Part.from_text(text=prompt)]),
    )
    return await parse_agent_response(events)


# <end_here>


if __name__ == "__main__":
    import hypercorn
    import asyncio

    from utils.utils import (
        fraud_agent_service,
        rate_comparison_agent_service,
        eligibility_agent_service,
    )

    restate_app = restate.app(
        services=[
            agent_service,
            fraud_agent_service,
            rate_comparison_agent_service,
            eligibility_agent_service,
        ]
    )
    conf = hypercorn.Config()
    conf.bind = ["0.0.0.0:9080"]
    asyncio.run(hypercorn.asyncio.serve(restate_app, conf))
