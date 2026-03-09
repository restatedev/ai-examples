"""
LLM Prompt Chaining

Build fault-tolerant processing pipelines that mix LLM steps with regular function calls.
If any step fails, Restate resumes from that point.

Input -> Parse Document -> Analyze Claim -> Convert Currency -> Process Payment -> Result
"""

import restate
from restate import RunOptions
from util.util import ClaimData, convert_currency, process_payment, ClaimPrompt
from util.litellm_call import llm_call

# <start_here>
claim_service = restate.Service("ClaimReimbursement")


@claim_service.handler()
async def process(ctx: restate.Context, req: ClaimPrompt) -> dict:
    """Sequentially chains LLM calls with regular function calls to process a claim."""

    # Step 1: Parse the claim document (LLM step)
    parsed = await ctx.run_typed(
        "Parse claim document",
        llm_call,
        RunOptions(max_attempts=3),
        messages=f"""Extract the claim amount, currency, category, and description.
        Document: {req.message}""",
        response_format=ClaimData,
    )
    claim = ClaimData.model_validate_json(parsed.content)

    # Step 2: Analyze the claim (LLM step)
    analysis = await ctx.run_typed(
        "Analyze claim",
        llm_call,
        RunOptions(max_attempts=3),
        messages=f"""Assess whether this claim is valid and determine the approved amount.
        Claim: {parsed.content}""",
    )

    # Step 3: Convert currency (regular step)
    amount_usd = await ctx.run_typed(
        "Convert currency",
        convert_currency,
        amount=claim.amount,
        source=claim.currency,
        target="USD",
    )

    # Step 4: Process reimbursement (regular step)
    confirmation = await ctx.run_typed(
        "Process payment",
        process_payment,
        claim_id=str(ctx.uuid()),
        amount=amount_usd,
    )

    return {
        "analysis": analysis.content,
        "amount_usd": amount_usd,
        "confirmation": confirmation,
    }


# <end_here>

if __name__ == "__main__":
    import asyncio
    import hypercorn

    app = restate.app(services=[claim_service])

    conf = hypercorn.Config()
    conf.bind = ["0.0.0.0:9080"]
    asyncio.run(hypercorn.asyncio.serve(app, conf))
