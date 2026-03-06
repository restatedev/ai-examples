"""
Human-in-the-Loop Pattern

Implement resilient human approval steps that suspend execution until feedback is received.
Durable promises survive crashes and can be recovered across process restarts.
"""

from datetime import timedelta

import restate
from pydantic import BaseModel
from restate import RunOptions

from util.litellm_call import llm_call
from util.util import InsuranceClaim, request_review, tool


class ClaimPrompt(BaseModel):
    message: str = (
        "Process my hospital bill of 2024-10-01 for 3000USD for a broken leg at General Hospital."
    )


# TOOL IMPLEMENTATION
# <start_here>
async def request_human_approval(ctx: restate.Context, claim: InsuranceClaim) -> str:
    # Create a recoverable approval promise
    approval_id, approval_promise = ctx.awakeable(type_hint=str)

    await ctx.run_typed(
        "Request review", request_review, claim=claim, approval_id=approval_id
    )

    # Suspend until human resolves the approval or until the timeout hits
    # Check the service logs to see how to resolve it over HTTP, e.g.:
    # curl http://localhost:8080/restate/awakeables/sign_.../resolve --json '"approved"'
    match await restate.select(
        approval=approval_promise,
        timeout=ctx.sleep(timedelta(hours=3)),
    ):
        case ["approval", approved]:
            return approved
        case _:
            return "Approval timed out - Evaluate with AI"
# <end_here>


claim_approval_agent = restate.Service("HumanClaimApprovalAgent")


@claim_approval_agent.handler()
async def run(ctx: restate.Context, req: ClaimPrompt) -> str | None:
    """Evaluate an insurance claim with optional human approval for high-value claims."""

    # LLM evaluates the claim and decides if human approval is needed
    result = await ctx.run_typed(
        "Evaluate claim",
        llm_call,  # Use your preferred LLM SDK here
        RunOptions(max_attempts=3),
        messages=f"""You are an insurance claim evaluation agent. Use these rules:
        - if the amount is more than 1000, ask for human approval using tools;
        - if the amount is less than 1000, decide by yourself.
        Claim: {req.message}""",
        tools=[
            tool(
                "request_human_approval",
                "Ask for human approval for high-value claims",
                InsuranceClaim.model_json_schema(),
            )
        ],
    )

    # If the LLM requests human approval, suspend until a human resolves it
    if (
        result.tool_calls
        and result.tool_calls[0].function.name == "request_human_approval"
    ):
        claim = InsuranceClaim.model_validate_json(
            result.tool_calls[0].function.arguments
        )
        return await request_human_approval(ctx, claim)

    return result.content


if __name__ == "__main__":
    import asyncio
    import hypercorn

    app = restate.app(services=[claim_approval_agent])

    conf = hypercorn.Config()
    conf.bind = ["0.0.0.0:9080"]
    asyncio.run(hypercorn.asyncio.serve(app, conf))
