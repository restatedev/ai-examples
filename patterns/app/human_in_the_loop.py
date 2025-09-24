import restate
from pydantic import BaseModel

from util import llm_call, notify_moderator

"""
Human-in-the-loop workflows with Restate

Implement resilient human approval steps that suspend execution until feedback is received.
These durable promises survive crashes and can be recovered on other processes on retries.
"""

content_moderator_svc = restate.Service("HumanInTheLoopService")

class Content(BaseModel):
    message: str = "Very explicit content that clearly violates policy."


@content_moderator_svc.handler()
async def moderate(ctx: restate.Context, content: Content) -> str:
    """Restate service handler as the durable entry point for content moderation."""

    # Durable step for LLM inference, auto retried & recovered
    analysis = await ctx.run_typed(
        "analyze_content",
        llm_call,
        prompt=f"Analyze content for policy violations. Return 'needsHumanReview' or your decision: {content}"
    )

    # Simple parsing - in real implementation you'd use proper JSON parsing
    if "needsHumanReview" in analysis:
        # Create a durable promise (awakeable),
        approval_id, approval_promise = ctx.awakeable(type_hint=str)

        # Notify moderator, identify the durable promise by its id
        await ctx.run_typed("notify_moderator", notify_moderator, content=content.message, approval_id=approval_id)

        # Pause for completion of the promise.
        # The workflow suspends here and resumes after the promise resolution.
        # Check the service logs to see how to resolve it, e.g.:
        # curl http://localhost:8080/restate/awakeables/sign_.../resolve --json '"approved"'
        return await approval_promise

    return analysis


