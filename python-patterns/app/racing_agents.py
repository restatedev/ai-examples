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
async def run(ctx: Context, query: Question):
    claude = ctx.service_call(deep_analysis, arg=query)
    openai = ctx.service_call(quick_response, arg=query)

    done, pending = await restate.wait_completed(claude, openai)

    # collect the completed results
    results = [await f for f in done]

    # cancel the pending calls
    for f in pending:
        call_future = typing.cast(RestateDurableCallFuture, f)
        ctx.cancel_invocation(await call_future.invocation_id())

    return results[0]


# <end_here>


@racing_agent.handler()
async def deep_analysis(ctx: Context, req: Question) -> str:
    output = await ctx.run_typed(
        "deep_analysis",
        llm_call,
        RunOptions(max_attempts=3),
        prompt=f"Analyze this thoroughly: {req}",
    )
    return output.content


@racing_agent.handler()
async def quick_response(ctx: Context, req: Question) -> str:
    output = await ctx.run_typed(
        "quick_response",
        llm_call,
        RunOptions(max_attempts=1),
        prompt=f"Quick answer: {req}",
    )
    return output.content
