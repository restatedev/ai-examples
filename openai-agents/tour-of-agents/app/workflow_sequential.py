import json

import restate
from agents import Agent
from pydantic import BaseModel
from restate.ext.openai import DurableRunner


class ClaimRequest(BaseModel):
    document: str
    claim_id: str


async def convert_currency(amount: float, source: str, target: str) -> float:
    """Convert currency (placeholder)."""
    return amount


async def process_payment(claim_id: str, amount: float) -> str:
    """Process payment (placeholder)."""
    return f"Payment processed for claim {claim_id}: ${amount}"


# <start_here>
claim_service = restate.Service("ClaimReimbursement")


@claim_service.handler()
async def process(ctx: restate.Context, req: ClaimRequest) -> dict:
    # Step 1: Parse the claim document (LLM step)
    parse_agent = Agent(
        name="DocumentParser",
        instructions="Extract the claim amount, currency, category, and description.",
    )
    parsed = await DurableRunner.run(parse_agent, req.document)
    claim = json.loads(parsed.final_output)

    # Step 2: Analyze the claim (LLM step)
    analysis_agent = Agent(
        name="ClaimsAnalyst",
        instructions="Assess whether this claim is valid and determine the approved amount.",
    )
    analysis = await DurableRunner.run(analysis_agent, f"Claim: {parsed.final_output}")

    # Step 3: Convert currency (regular step)
    amount_usd = await ctx.run_typed(
        "Convert currency",
        convert_currency,
        amount=claim["amount"],
        source=claim["currency"],
        target="USD",
    )

    # Step 4: Process reimbursement (regular step)
    confirmation = await ctx.run_typed(
        "Process payment",
        process_payment,
        claim_id=req.claim_id,
        amount=amount_usd,
    )

    return {
        "analysis": analysis.final_output,
        "amount_usd": amount_usd,
        "confirmation": confirmation,
    }


# <end_here>


if __name__ == "__main__":
    import hypercorn
    import asyncio

    app = restate.app(services=[claim_service])
    conf = hypercorn.Config()
    conf.bind = ["0.0.0.0:9080"]
    asyncio.run(hypercorn.asyncio.serve(app, conf))
