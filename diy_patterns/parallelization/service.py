import restate
from pydantic import BaseModel
from a_orchestrating_llm_calls.util.util import llm_call

"""
Parallelization with Restate

This example demonstrates how to parallelize multiple LLM calls and gather their results.
Restate kicks of all the tasks in parallel and manages their execution to run to completion (retries + recovery).

If you ask it to run the task in 5 different models, and after 3 have given there response, the service crashes.
Then only the 2 remaining tasks will be retried. Restate will have persisted the results of the other 3 tasks.

This example is a translation of the Anthropic AI agents Python notebook examples:
https://github.com/anthropics/anthropic-cookbook/blob/main/patterns/agents/
"""

parallelization_svc = restate.Service("ParallelizationService")


class ParallelizationRequest(BaseModel):
    prompt: str
    inputs: list[str]


@parallelization_svc.handler()
async def run_in_parallel(
    ctx: restate.Context, req: ParallelizationRequest
) -> list[str]:
    futures = [
        ctx.run(
            f"LLM call {item}",
            lambda item=item: llm_call(f"{req.prompt}\nInput: {item}"),
        )
        for item in req.inputs
    ]
    results_done = await restate.gather(*futures)
    results = [await result for result in results_done]
    return results
