import restate
from google.adk import Runner
from google.adk.agents.llm_agent import Agent
from google.adk.apps import App
from google.adk.tools.tool_context import ToolContext
from google.genai.types import Content, Part
from restate.ext.adk import RestatePlugin, RestateSessionService

from app.utils.models import ClaimPrompt, InsuranceClaim
from app.utils.utils import request_human_review

APP_NAME = "agents"


# TOOLS
async def human_approval(tool_context: ToolContext, claim: InsuranceClaim) -> str:
    """Ask for human approval for high-value claims."""
    restate_context = tool_context.session.state["restate_context"]

    # Create an awakeable for human approval
    approval_id, approval_promise = restate_context.awakeable(type_hint=str)

    # Request human review
    await restate_context.run_typed(
        "Request review",
        request_human_review,
        claim=claim,
        awakeable_id=approval_id,
    )

    # Wait for human approval
    return await approval_promise


# AGENT
agent = Agent(
    model="gemini-2.5-flash",
    name="claim_approval_agent",
    description="Insurance claim evaluation agent that handles human approval workflows.",
    instruction="""You are an insurance claim evaluation agent. Use these rules: 
    - if the amount is more than 1000, ask for human approval using tools; 
    - if the amount is less than 1000, decide by yourself.""",
    tools=[human_approval],
)


app = App(name=APP_NAME, root_agent=agent, plugins=[RestatePlugin()])
session_service = RestateSessionService()

agent_service = restate.VirtualObject("HumanClaimApprovalAgent")


# HANDLER
@agent_service.handler()
async def run(ctx: restate.ObjectContext, req: ClaimPrompt) -> str | None:
    runner = Runner(app=app, session_service=session_service)
    events = runner.run_async(
        user_id=ctx.key(),
        session_id=req.session_id,
        new_message=Content(role="user", parts=[Part.from_text(text=req.message)]),
    )

    final_response = None
    async for event in events:
        if event.is_final_response() and event.content and event.content.parts:
            if event.content.parts[0].text:
                final_response = event.content.parts[0].text
    return final_response
