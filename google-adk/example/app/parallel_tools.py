import restate
from google.adk import Runner
from google.adk.agents.llm_agent import Agent
from google.adk.apps import App
from google.adk.tools.tool_context import ToolContext
from google.genai.types import Content, Part
from typing import List

from app.utils.models import InsuranceClaim
from app.utils.utils import check_eligibility, compare_to_standard_rates, check_fraud

from middleware.restate_plugin import RestatePlugin
from middleware.restate_session_service import RestateSessionService
from middleware.restate_utils import restate_overrides

APP_NAME = "agents"


async def calculate_metrics(
    tool_context: ToolContext,
    claim: InsuranceClaim,
) -> List[str]:
    """Calculate claim metrics using parallel execution."""
    restate_context = tool_context.session.state["restate_context"]

    # Run tools/steps in parallel with durable execution
    results_done = await restate.gather(
        restate_context.run_typed("eligibility", check_eligibility, claim=claim),
        restate_context.run_typed("cost", compare_to_standard_rates, claim=claim),
        restate_context.run_typed("fraud", check_fraud, claim=claim),
    )
    return [await result for result in results_done]


# AGENT
agent = Agent(
    model="gemini-2.0-flash",
    name="parallel_tools_agent",
    description="Analyzes insurance claims using parallel tool execution.",
    instruction="You are a claim analysis agent that analyzes insurance claims. "
    "Use your tools to calculate key metrics and decide whether to approve the claim.",
    tools=[calculate_metrics],
)


app = App(name=APP_NAME, root_agent=agent, plugins=[RestatePlugin()])
session_service = RestateSessionService()


agent_service = restate.VirtualObject("ParallelToolClaimAgent")


@agent_service.handler()
async def run(ctx: restate.ObjectContext, claim: InsuranceClaim) -> str:
    prompt = f"""Analyze the claim {claim.model_dump_json()}. 
    Use your tools to calculate key metrics and decide whether to approve."""

    session_id = ctx.key()
    with restate_overrides(ctx):
        await session_service.create_session(
            app_name=APP_NAME, user_id=claim.user_id, session_id=session_id
        )

        runner = Runner(app=app, session_service=session_service)
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
