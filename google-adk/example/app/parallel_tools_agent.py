import restate
from google.adk.agents.llm_agent import Agent
from google.adk.tools.tool_context import ToolContext
from google.genai import types as genai_types
from pydantic import BaseModel
from typing import List

from middleware.middleware import durable_model_calls
from middleware.restate_runner import RestateRunner
from middleware.restate_session_service import RestateSessionService
from middleware.restate_tools import restate_tools

APP_NAME = "agents"


class InsuranceClaim(BaseModel):
    claim_id: str
    claim_type: str
    amount: float
    description: str


def check_eligibility(claim: InsuranceClaim) -> str:
    """Check if claim is eligible for processing."""
    if claim.amount > 100000:
        return f"Claim {claim.claim_id} not eligible: Amount exceeds maximum coverage"
    elif claim.claim_type.lower() not in ["medical", "auto", "property"]:
        return f"Claim {claim.claim_id} not eligible: Invalid claim type"
    else:
        return f"Claim {claim.claim_id} is eligible for processing"


def compare_to_standard_rates(claim: InsuranceClaim) -> str:
    """Compare claim amount to standard rates."""
    if claim.amount > 75000:
        return f"Claim {claim.claim_id} cost analysis: High-value claim, recommend additional review"
    elif claim.amount < 1000:
        return f"Claim {claim.claim_id} cost analysis: Low-value claim, fast-track processing"
    else:
        return f"Claim {claim.claim_id} cost analysis: Standard processing recommended"


def check_fraud(claim: InsuranceClaim) -> str:
    """Check for potential fraud indicators."""
    if claim.amount > 50000 and "accident" in claim.description.lower():
        return f"Claim {claim.claim_id} flagged: High amount with accident keywords - potential fraud risk"
    elif claim.description.lower().count("total loss") > 1:
        return f"Claim {claim.claim_id} flagged: Suspicious language patterns detected"
    else:
        return f"Claim {claim.claim_id} appears legitimate based on fraud analysis"


# <start_here>
async def calculate_metrics(
    tool_context: ToolContext,
    claim_id: str,
    claim_type: str,
    amount: float,
    description: str,
) -> List[str]:
    """Calculate claim metrics using parallel execution."""
    restate_context = tool_context.session.state["restate_context"]

    claim = InsuranceClaim(
        claim_id=claim_id, claim_type=claim_type, amount=amount, description=description
    )

    # Run tools/steps in parallel with durable execution
    results_done = await restate.gather(
        restate_context.run_typed("eligibility", check_eligibility, claim=claim),
        restate_context.run_typed("cost", compare_to_standard_rates, claim=claim),
        restate_context.run_typed("fraud", check_fraud, claim=claim),
    )
    return [await result for result in results_done]


# <end_here>


agent_service = restate.VirtualObject("ParallelToolClaimAgent")


@agent_service.handler()
async def run(ctx: restate.ObjectContext, claim: InsuranceClaim) -> str:
    user_id = "user"

    parallel_tools_agent = Agent(
        model=durable_model_calls(ctx, "gemini-2.5-flash"),
        name="parallel_tools_agent",
        description="Analyzes insurance claims using parallel tool execution.",
        instruction="You are a claim analysis agent that analyzes insurance claims. Use your tools to calculate key metrics and decide whether to approve the claim.",
        tools=restate_tools(calculate_metrics),
    )

    session_service = RestateSessionService(ctx)
    await session_service.create_session(
        app_name=APP_NAME, user_id=user_id, session_id=ctx.key()
    )

    runner = RestateRunner(
        restate_context=ctx,
        agent=parallel_tools_agent,
        app_name=APP_NAME,
        session_service=session_service,
    )

    events = runner.run_async(
        user_id=user_id,
        session_id=ctx.key(),
        new_message=genai_types.Content(
            role="user",
            parts=[
                genai_types.Part.from_text(
                    text=f"Analyze the claim {claim.model_dump_json()}. "
                    "Use your tools to calculate key metrics and decide whether to approve."
                )
            ],
        ),
    )

    final_response = ""
    async for event in events:
        if event.is_final_response() and event.content and event.content.parts:
            final_response = event.content.parts[0].text

    return final_response
