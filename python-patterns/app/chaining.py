import restate
from pydantic import BaseModel
from restate import RunOptions

from .util.litellm_call import llm_call

"""
LLM Prompt Chaining

Build fault-tolerant processing pipelines where each step transforms the previous step's output.
If any step fails, Restate automatically resumes from that exact point.

Input → Analysis → Extraction → Summary → Result
"""

call_chaining_svc = restate.Service("CallChainingService")

example_prompt = """Q3 Performance Summary:
Our customer satisfaction score rose to 92 points this quarter.
Revenue grew by 45% compared to last year.
Market share is now at 23% in our primary market.
Customer churn decreased to 5% from 8%."""

class Prompt(BaseModel):
    message: str = example_prompt


@call_chaining_svc.handler()
async def run(ctx: restate.Context, prompt: Prompt) -> str:
    """Chains multiple LLM calls sequentially, where each step processes the previous step's output."""

    # Step 1: Process the initial input with the first prompt
    result = await ctx.run_typed(
        "Extract metrics",
        llm_call,
        RunOptions(max_attempts=3),
        prompt=f"Extract only the numerical values and their associated metrics from the text. "
        f"Format each as 'metric name: metric' on a new line. Input: {prompt.message}",
    )

    # Step 2: Process the result from Step 1
    result2 = await ctx.run_typed(
        "Sort metrics",
        llm_call,
        RunOptions(max_attempts=3),
        prompt=f"Sort all lines in descending order by numerical value. Input: {result}",
    )

    # Step 3: Process the result from Step 2
    result3 = await ctx.run_typed(
        "Format as table",
        llm_call,
        RunOptions(max_attempts=3),
        prompt=f"Format the sorted data as a markdown table with columns 'Metric Name' and 'Value'. Input: {result2}",
    )

    return result3.content
