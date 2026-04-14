import restate
from datetime import timedelta
from google.adk import Runner
from google.adk.agents.llm_agent import Agent
from google.adk.apps import App
from google.genai.types import Content, Part
from restate.ext.adk import RestatePlugin, restate_context, RestateSessionService
from utils.models import ClaimPrompt, InsuranceClaim
from utils.utils import request_review, parse_agent_response

APP_NAME = "agents"


# TOOLS
# <start_here>
async def human_approval(claim: InsuranceClaim) -> str:
    """Ask for human approval for high-value claims."""
    # Create an awakeable for human approval
    approval_id, approval_promise = restate_context().awakeable(type_hint=str)

    # Request human review
    await restate_context().run_typed(
        "Request review",
        request_review,
        claim=claim,
        awakeable_id=approval_id,
    )

    # Wait for human approval for at most 3 hours to reach our SLA
    match await restate.select(
        approval=approval_promise,
        timeout=restate_context().sleep(timedelta(hours=3)),
    ):
        case ["approval", approved]:
            return "Approved" if approved else "Rejected"
        case _:
            return "Approval timed out - Evaluate with AI"


# <end_here>


agent = Agent(
    model="gemini-2.5-flash",
    name="claim_approval_agent",
    instruction="""You are an insurance claim evaluation agent. Use these rules: 
    - if the amount is more than 1000, ask for human approval using tools; 
    - if the amount is less than 1000, decide by yourself.""",
    tools=[human_approval],
)


app = App(name=APP_NAME, root_agent=agent, plugins=[RestatePlugin()])
runner = Runner(app=app, session_service=RestateSessionService())

agent_service = restate.VirtualObject("HumanClaimApprovalWithTimeoutsAgent")


@agent_service.handler()
async def run(ctx: restate.ObjectContext, req: ClaimPrompt) -> str | None:
    events = runner.run_async(
        user_id=ctx.key(),
        session_id=req.session_id,
        new_message=Content(role="user", parts=[Part.from_text(text=req.message)]),
    )
    return await parse_agent_response(events)


if __name__ == "__main__":
    import hypercorn
    import asyncio

    restate_app = restate.app(services=[agent_service])
    conf = hypercorn.Config()
    conf.bind = ["0.0.0.0:9080"]
    asyncio.run(hypercorn.asyncio.serve(restate_app, conf))
