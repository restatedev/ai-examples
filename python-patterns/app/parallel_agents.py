import restate
from pydantic import BaseModel

from .util.litellm_call import llm_call

"""
LLM Parallel Processing

Process multiple inputs simultaneously with the same prompt.
If any task fails, Restate retries only the failed tasks; completed results are preserved.

Task A ↘
Task B → [Wait on Results] → Results A, B, C
Task C ↗
"""

parallelization_svc = restate.Service("ParallelAgentsService")

# Example input text to analyze
example_prompt = (
    "Our Q3 results exceeded all expectations! Customer satisfaction reached 95%, revenue grew "
    "by 40% year-over-year, and we successfully launched three new product features. "
    "The team worked incredibly hard to deliver these outcomes despite supply chain challenges. "
    "Our market share increased to 23%, and we're well-positioned for continued growth in Q4."
)


class Prompt(BaseModel):
    message: str = example_prompt


@parallelization_svc.handler()
async def analyze_text(ctx: restate.Context, prompt: Prompt) -> list[str]:
    """Analyzes multiple aspects of the text in parallel."""

    # Create parallel tasks - each runs independently
    sentiment_task = ctx.run_typed(
        "Analyze sentiment",
        llm_call,
        restate.RunOptions(max_attempts=3),
        prompt=f"Analyze sentiment (positive/negative/neutral): {prompt}",
    )

    key_points_task = ctx.run_typed(
        "Extract key points",
        llm_call,
        restate.RunOptions(max_attempts=3),
        prompt=f"Extract 3 key points as bullets: {prompt}",
    )

    summary_task = ctx.run_typed(
        "Summarize",
        llm_call,
        restate.RunOptions(max_attempts=3),
        prompt=f"Summarize in one sentence: {prompt}",
    )

    # Wait for all tasks to complete
    results = await restate.gather(sentiment_task, key_points_task, summary_task)

    # Gather and collect results
    return [(await result).content for result in results]
