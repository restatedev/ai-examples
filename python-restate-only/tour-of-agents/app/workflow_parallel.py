"""
Parallel Agents

Process multiple inputs simultaneously with specialized agents.
If any task fails, Restate retries only the failed tasks while preserving completed results.

Task A ↘
Task B → [Wait on Results] → Results A, B, C
Task C ↗
"""

import json

import restate
from restate import RunOptions

from util.litellm_call import llm_call
from util.util import ClaimData

# <start_here>
parallelization_svc = restate.Service("ParallelAgentsService")


@parallelization_svc.handler()
async def analyze(ctx: restate.Context, claim: ClaimData) -> list[str | None]:
    """Analyzes a claim in parallel with specialized agents."""

    # Create parallel tasks - each runs independently
    claim_json = json.dumps(claim.model_dump())
    eligibility = ctx.run_typed(
        "Eligibility agent",
        llm_call,
        RunOptions(max_attempts=3),
        messages="Decide whether the following claim is eligible for reimbursement."
        " Respond with eligible if it's a medical claim, and not eligible otherwise."
        f"\n\nClaim: {claim_json}",
    )
    fraud = ctx.run_typed(
        "Fraud agent",
        llm_call,
        RunOptions(max_attempts=3),
        messages="Decide whether the cost of the claim is reasonable given the treatment."
        " Respond with reasonable or not reasonable."
        f"\n\nClaim: {claim_json}",
    )
    rate = ctx.run_typed(
        "Rate comparison agent",
        llm_call,
        RunOptions(max_attempts=3),
        messages="Decide whether the claim is fraudulent."
        " Always respond with low risk, medium risk, or high risk."
        f"\n\nClaim: {claim_json}",
    )

    # Wait for all tasks to complete
    await restate.gather([eligibility, fraud, rate])

    # Make final decision
    return ctx.run_typed(
        "Rate comparison agent",
        llm_call,
        RunOptions(max_attempts=3),
        messages=f"Decide about claim: {claim.model_dump_json()}. "
        "Base your decision on the following analyses:"
        f"Eligibility: {await eligibility} Cost {await rate} Fraud: {await fraud}",
    )


# <end_here>

if __name__ == "__main__":
    import asyncio
    import hypercorn

    app = restate.app(services=[parallelization_svc])

    conf = hypercorn.Config()
    conf.bind = ["0.0.0.0:9080"]
    asyncio.run(hypercorn.asyncio.serve(app, conf))
