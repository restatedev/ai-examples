"""
LLM Prompt Chaining

Build fault-tolerant processing pipelines where each step transforms the previous output.
If any step fails, Restate resumes from that point.

Input → Analysis → Extraction → Summary → Result
"""

import restate
from pydantic import BaseModel
from restate import RunOptions

from .util.litellm_call import llm_call


call_chaining_svc = restate.Service("CallChainingService")

example_prompt = """Q3 Performance Summary:
Our customer satisfaction score rose to 92 points this quarter.
Revenue grew by 45% compared to last year.
Market share is now at 23% in our primary market.
Customer churn decreased to 5% from 8%."""


class Report(BaseModel):
    text: str = example_prompt


@call_chaining_svc.handler()
async def process_report(ctx: restate.Context, report: Report) -> str | None:
    """Sequentially chains multiple LLM calls, each transforming the prior output."""

    # Step 1: Extract metrics
    extract = await ctx.run_typed(
        "Extract metrics",
        llm_call,
        RunOptions(max_attempts=3),
        prompt=(
            "Extract numerical values and their metrics from the text. "
            f"Format as 'Metric: Value' per line. Input: {report.text}"
        ),
    )

    # Step 2: Sort by value
    sorted_metrics = await ctx.run_typed(
        "Sort metrics",
        llm_call,
        RunOptions(max_attempts=3),
        prompt=f"Sort lines in descending order by value. Input: {extract}",
    )

    # Step 3: Format as table
    table = await ctx.run_typed(
        "Format as table",
        llm_call,
        RunOptions(max_attempts=3),
        prompt=(
            "Format the data as a markdown table with columns "
            f"'Metric Name' and 'Value'. Input: {sorted_metrics}"
        ),
    )

    return table.content
