import restate
from pydantic import BaseModel
from util.util import llm_call

"""
Prompt-chaining with Restate

This example demonstrates how to chain multiple LLM calls sequentially, passing results between steps.
Restate persists the intermediate results to allow for recovery in case of failure.

If you pass it 100 prompts and it fails on the 80st, Restate will start the retry from the 80st prompt.

This example is a translation of the Anthropic AI agents Python notebook examples:
https://github.com/anthropics/anthropic-cookbook/blob/main/patterns/agents/
"""

call_chaining_svc = restate.Service("CallChainingService")


class ChainRequest(BaseModel):
    input: str
    prompts: list[str]


@call_chaining_svc.handler()
async def chain_call(ctx: restate.Context, req: ChainRequest) -> str:
    result = req.input
    for i, prompt in enumerate(req.prompts, 1):
        print(f"\nStep {i}:")
        result = await ctx.run(
            f"LLM call ${i}", lambda: llm_call(f"{prompt}\nInput: {result}")
        )
        print(result)
    return result
