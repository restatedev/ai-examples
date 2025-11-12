"""
Human-in-the-Loop Pattern

Implement resilient human approval steps that suspend execution until feedback is received.
Durable promises survive crashes and can be recovered across process restarts.
"""

import restate
from restate import RunOptions

from .util.litellm_call import llm_call
from .util.util import notify_moderator, Content, tool

content_moderator = restate.Service("HumanInTheLoopService")


@content_moderator.handler()
async def moderate(ctx: restate.Context, content: Content) -> str | None:
    """Moderate content with optional human review."""

    # Run LLM moderation
    result = await ctx.run_typed(
        "moderate",
        llm_call,
        RunOptions(max_attempts=3),
        system="You are a content moderation agent. Decide if the content violates policy.",
        prompt=content.message,
        tools=[tool("get_human_review", "Request human review if policy violation is uncertain.")],
    )

    # Handle human review request
    if result.tool_calls and result.tool_calls[0].function.name == "get_human_review":
        # Create a recoverable approval promise
        approval_id, approval_promise = ctx.awakeable(type_hint=str)

        await ctx.run_typed(
            "notify moderator",
            notify_moderator,
            content=content,
            approval_id=approval_id,
        )

        # Suspend until moderator resolves the approval
        # Check the service logs to see how to resolve it over HTTP, e.g.:
        # curl http://localhost:8080/restate/awakeables/sign_.../resolve --json '"approved"'
        return await approval_promise

    return result.content
