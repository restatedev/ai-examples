import typing
import restate
from pydantic import BaseModel

from restate import Service, Context, RestateDurableCallFuture, RunOptions
from app.util.litellm_call import llm_call


class Question(BaseModel):
    message: str = "What's the best approach to learn machine learning?"


# <start_here>
racing_agent = Service("RacingAgent")


@racing_agent.handler()
async def run(ctx: Context, query: Question) -> str | None:
    """Run two approaches in parallel and return the fastest response."""
    # Start both service calls concurrently
    slow_response = ctx.service_call(think_longer, arg=query)
    quick_response = ctx.service_call(respond_quickly, arg=query)

    done, pending = await restate.wait_completed(slow_response, quick_response)

    # cancel the pending calls
    for f in pending:
        call_future = typing.cast(RestateDurableCallFuture, f)
        ctx.cancel_invocation(await call_future.invocation_id())

    # return the fastest result
    return await done[0]


# <end_here>


@racing_agent.handler()
async def think_longer(ctx: Context, req: Question) -> str | None:
    output = await ctx.run_typed(
        "Deep analysis",
        llm_call,
        RunOptions(max_attempts=3),
        messages=f"Analyze this thoroughly: {req}",
    )
    return output.content


@racing_agent.handler()
async def respond_quickly(ctx: Context, req: Question) -> str | None:
    output = await ctx.run_typed(
        "Quick response",
        llm_call,
        RunOptions(max_attempts=3),
        messages=f"Quick answer: {req}",
    )
    return output.content
