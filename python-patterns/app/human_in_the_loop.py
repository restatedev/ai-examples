import restate
from restate import RunOptions

from .util.litellm_call import llm_call
from .util.util import notify_moderator, Content

"""
Human-in-the-loop workflows with Restate

Implement resilient human approval steps that suspend execution until feedback is received.
These durable promises survive crashes and can be recovered on other processes on retries.
"""
content_moderator_svc = restate.Service("HumanInTheLoopService")


@content_moderator_svc.handler()
async def moderate(ctx: restate.Context, content: Content) -> str:
    """Moderate content with human-in-the-loop review"""

    # Durable step for LLM inference, auto retried & recovered
    result = await ctx.run_typed(
        "moderate",
        llm_call,
        RunOptions(max_attempts=3),
        prompt=f"Decide whether content violates the policy."
        f"Use the human review tool if you are not sure."
        f"Content: {content}",
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "get_human_review",
                    "description": "Get human review for content that may violate policy.",
                },
            }
        ],
    )

    # request human review, if ordered by LLM
    if result.tool_calls and result.tool_calls[0].function.name == "get_human_review":
        # Create a durable promise (awakeable),
        approval_id, approval_promise = ctx.awakeable(type_hint=str)

        # Notify moderator, identify the durable promise by its id
        await ctx.run_typed(
            "notify_moderator",
            notify_moderator,
            content=content,
            approval_id=approval_id,
        )

        # Pause for completion of the promise.
        # The workflow suspends here and resumes after the promise resolution.
        # Check the service logs to see how to resolve it, e.g.:
        # curl http://localhost:8080/restate/awakeables/sign_.../resolve --json '"approved"'
        return await approval_promise

    return result.content
