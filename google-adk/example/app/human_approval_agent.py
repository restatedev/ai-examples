import restate
from google.adk.agents.llm_agent import Agent
from google.adk.tools.tool_context import ToolContext
from google.genai import types as genai_types

from app.utils.models import ClaimPrompt
from app.utils.utils import request_human_review
from middleware.middleware import durable_model_calls
from middleware.restate_runner import RestateRunner
from middleware.restate_session_service import RestateSessionService
from middleware.restate_tools import restate_tools

APP_NAME = "agents"

# <start_here>
async def human_approval(tool_context: ToolContext, claim_id: str, amount: float, description: str) -> str:
    """Ask for human approval for high-value claims."""
    restate_context = tool_context.session.state["restate_context"]

    # Create an awakeable for human approval
    approval_id, approval_promise = restate_context.awakeable(type_hint=str)

    # Request human review
    await restate_context.run_typed(
        "Request review", request_human_review, claim_id=claim_id, amount=amount, description=description, awakeable_id=approval_id
    )

    # Wait for human approval
    return await approval_promise
# <end_here>


agent_service = restate.VirtualObject("HumanClaimApprovalAgent")


@agent_service.handler()
async def run(ctx: restate.ObjectContext, prompt: ClaimPrompt) -> str:
    user_id = "user"

    agent = Agent(
        model=durable_model_calls(ctx, 'gemini-2.5-flash'),
        name='claim_approval_agent',
        description="Insurance claim evaluation agent that handles human approval workflows.",
        instruction="You are an insurance claim evaluation agent. Use these rules: if the amount is more than 1000, ask for human approval; if the amount is less than 1000, decide by yourself. Use the human_approval tool when needed.",
        tools=restate_tools(human_approval),
    )

    session_service = RestateSessionService(ctx)
    await session_service.create_session(
        app_name=APP_NAME, user_id=user_id, session_id=ctx.key()
    )

    runner = RestateRunner(restate_context=ctx, agent=agent, app_name=APP_NAME, session_service=session_service)

    events = runner.run_async(
        user_id=user_id,
        session_id=ctx.key(),
        new_message=genai_types.Content(
            role="user",
            parts=[genai_types.Part.from_text(text=prompt.message)]
        )
    )

    final_response = ""
    async for event in events:
        if event.is_final_response() and event.content and event.content.parts:
            final_response = event.content.parts[0].text

    return final_response
