import restate
from google.adk import Runner
from google.adk.agents.llm_agent import Agent
from google.adk.apps import App
from google.genai.types import Content, Part
from restate.ext.adk import RestatePlugin, restate_context, RestateSessionService

from utils.models import ClaimPrompt, InsuranceClaim
from utils.utils import request_human_review, parse_agent_response

APP_NAME = "agents"


# <start_wf>
# Sub-workflow service for human approval
human_approval_workflow = restate.VirtualObject("HumanApprovalWorkflow")


@human_approval_workflow.handler()
async def review(ctx: restate.ObjectContext, claim: InsuranceClaim) -> str:
    """Request human approval for a claim and wait for response."""
    # Create an awakeable that can be resolved via HTTP
    approval_id, approval_promise = ctx.awakeable(type_hint=str)

    # Request human review
    await ctx.run_typed(
        "Request review", request_human_review, claim=claim, awakeable_id=approval_id
    )

    # Wait for human approval
    return await approval_promise


# <end_wf>


# <start_here>
async def human_approval(claim: InsuranceClaim) -> str:
    """Ask for human approval for high-value claims."""
    return await restate_context().service_call(review, claim)


# <end_here>

# AGENT
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

agent_service = restate.VirtualObject("SubWorkflowClaimApprovalAgent")


# HANDLER
@agent_service.handler()
async def run(ctx: restate.ObjectContext, req: ClaimPrompt) -> str | None:
    events = runner.run_async(
        user_id=req.user_id,
        session_id=req.session_id,
        new_message=Content(role="user", parts=[Part.from_text(text=req.message)]),
    )
    return await parse_agent_response(events)


if __name__ == "__main__":
    import hypercorn
    import asyncio

    restate_app = restate.app(services=[agent_service, human_approval_workflow])
    conf = hypercorn.Config()
    conf.bind = ["0.0.0.0:9080"]
    asyncio.run(hypercorn.asyncio.serve(restate_app, conf))
