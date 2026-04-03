"""
LLM Prompt Chaining

Build fault-tolerant processing pipelines that mix LLM steps with regular function calls.
If any step fails, Restate resumes from that point.

Input -> Parse Document -> Analyze Claim -> Convert Currency -> Process Payment -> Result
"""

import restate
from restate import RunOptions

from util.util import ClaimData, ClaimEvaluation, ClaimPrompt, convert_currency, process_payment
from util.litellm_call import llm_call

# <start_here>
agent_service = restate.Service("ClaimReimbursement")


@agent_service.handler()
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
    if not parsed.content:
        raise restate.TerminalError("LLM failed to parse claim document.")
    claim = ClaimData.model_validate_json(parsed.content)

    # Step 2: Analyze the claim (LLM step)
    response = await ctx.run_typed(
        "Evaluate claim",
        llm_call,
        RunOptions(max_attempts=3),
        messages=f"""Assess whether this claim is valid and determine the approved amount.
        Claim: {parsed.content}""",
        response_format=ClaimEvaluation,
    )
    if not response.content:
        raise restate.TerminalError("LLM failed to analyze claim.")
    evaluation = ClaimEvaluation.model_validate_json(response.content)
    if not evaluation.valid:
        return {"analysis": "Claim is invalid."}


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
        "analysis": "Claim is valid.",
        "amount_usd": amount_usd,
        "confirmation": confirmation,
    }


# <end_here>
