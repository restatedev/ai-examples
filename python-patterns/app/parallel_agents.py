"""
Parallel Agents

Process multiple inputs simultaneously with specialized agents.
If any task fails, Restate retries only the failed tasks while preserving completed results.

Task A ↘
Task B → [Wait on Results] → Results A, B, C
Task C ↗
"""

import restate
from pydantic import BaseModel
from restate import RunOptions

from .util.litellm_call import llm_call


class Text(BaseModel):
    content: str = (
        "Our Q3 results exceeded all expectations! Customer satisfaction reached 95%, revenue grew "
        "by 40% year-over-year, and we successfully launched three new product features. "
        "The team worked incredibly hard to deliver these outcomes despite supply chain challenges. "
        "Our market share increased to 23%, and we're well-positioned for continued growth in Q4."
    )


parallelization_svc = restate.Service("ParallelAgentsService")


@parallelization_svc.handler()
async def analyze(ctx: restate.Context, text: Text) -> list[str]:
    """Analyzes multiple aspects of the text in parallel."""

    # Create parallel tasks - each runs independently
    tasks = [
        ctx.run_typed(
            "Analyze sentiment",
            llm_call,  # Use your preferred LLM SDK here
            RunOptions(max_attempts=3),
            prompt=f"Analyze sentiment (positive/negative/neutral): {text}",
        ),
        ctx.run_typed(
            "Extract key points",
            llm_call,
            RunOptions(max_attempts=3),
            prompt=f"Extract 3 key points as bullets: {text}",
        ),
        ctx.run_typed(
            "Summarize",
            llm_call,
            RunOptions(max_attempts=3),
            prompt=f"Summarize in one sentence: {text}",
        ),
    ]

    # Wait for all tasks to complete
    await restate.gather(*tasks)

    # Gather and collect results
    return [(await task).content for task in tasks]
