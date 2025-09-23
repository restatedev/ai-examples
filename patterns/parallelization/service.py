import restate
from pydantic import BaseModel
from util.util import llm_call

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


import restate
from pydantic import BaseModel
from util.util import llm_call

"""
Prompt-chaining with Restate

This example demonstrates how to chain multiple LLM calls sequentially, where each step
processes the output from the previous step. This creates a processing pipeline.

Key benefits:
1. Sequential processing: Each step builds on the previous result
2. Fault tolerance: If a step fails, Restate resumes from that exact step
3. State persistence: Intermediate results are automatically saved

Example flow:
Input → Step 1 → Step 2 → Step 3 → Final Result

If Step 2 fails, Restate will retry from Step 2 (not from the beginning),
preserving the results from Step 1.

This example is a translation of the Anthropic AI agents Python notebook examples:
https://github.com/anthropics/anthropic-cookbook/blob/main/patterns/agents/
"""

call_chaining_svc = restate.Service("CallChainingService")


class ChainRequest(BaseModel):
    input: str
    prompts: list[str]


# @call_chaining_svc.handler()
# async def chain_call(ctx: restate.Context, input: str) -> str:
#     """
#     Chains multiple LLM calls sequentially, where each step processes the previous step's output.
#
#     Each ctx.run() call represents a separate, recoverable step in the chain.
#     If any step fails, Restate will retry from that specific step, preserving all previous results.
#     """
#
#     # Step 1: Process the initial input with the first prompt
#     result = await ctx.run_typed(
#         "Analyze sentiment",
#         llm_call,
#         prompt=f"Analyze the sentiment of this text and classify it as positive, negative, or neutral. Input: {input}"
#     )
#     print(f"Step 1 result: {result}")
#
#     # Step 2: Process the result from Step 1
#     result = await ctx.run_typed(
#         "Analyze sentiment",
#         llm_call,
#         prompt=f"Extract the key points from the text and list them as bullet points. Input: {result}"
#     )
#     print(f"Step 2 result: {result}")
#
#
#     # Step 3: Process the result from Step 2
#     result = await ctx.run_typed(
#         "Analyze sentiment",
#         llm_call,
#         prompt=f"Generate a brief one-sentence summary of the main message. Input: {result}"
#     )
#     print(f"Step 3 result: {result}")
#
#     return result
