import restate

from google.adk import Runner
from google.adk.agents.llm_agent import Agent
from google.adk.apps import App
from google.genai.types import Content, Part
from typing import List

from restate.ext.adk import RestatePlugin, RestateSessionService, restate_object_context

from app.utils.models import InsuranceClaim
from app.utils.utils import check_eligibility, compare_to_standard_rates, check_fraud

APP_NAME = "agents"

# <start_here>
async def calculate_metrics(claim: InsuranceClaim) -> List[str]:
    """Calculate claim metrics using parallel execution."""
    ctx = restate_object_context()

    # Run tools/steps in parallel with durable execution
    results_done = await restate.gather(
        ctx.run_typed("eligibility", check_eligibility, claim=claim),
        ctx.run_typed("cost", compare_to_standard_rates, claim=claim),
        ctx.run_typed("fraud", check_fraud, claim=claim),
    )
    return [await result for result in results_done]
# <end_here>


# AGENT
agent = Agent(
    model="gemini-2.5-flash",
    name="parallel_tools_agent",
    instruction="You are a claim analysis agent that analyzes insurance claims. "
    "Use your tools to calculate key metrics and decide whether to approve the claim.",
    tools=[calculate_metrics],
)


app = App(name=APP_NAME, root_agent=agent, plugins=[RestatePlugin()])
runner = Runner(app=app, session_service=RestateSessionService())

agent_service = restate.VirtualObject("ParallelToolClaimAgent")


@agent_service.handler()
async def run(ctx: restate.ObjectContext, claim: InsuranceClaim) -> str | None:
    prompt = f"Analyze the claim: {claim.model_dump_json()}."
    events = runner.run_async(
        user_id=ctx.key(),
        session_id=claim.session_id,
        new_message=Content(role="user", parts=[Part.from_text(text=prompt)]),
    )

    final_response = None
    async for event in events:
        if event.is_final_response() and event.content and event.content.parts:
            if event.content.parts[0].text:
                final_response = event.content.parts[0].text
    return final_response
