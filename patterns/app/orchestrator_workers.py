import restate

from pydantic import BaseModel

from .util.litellm_call import llm_call
from .util.util import parse_instructions

"""
LLM Orchestrator-Workers

Break down complex tasks into specialized subtasks and execute them in parallel.
If any worker fails, Restate retries only that worker—other completed work is preserved.

Task → Orchestrator → [Worker A, Worker B, Worker C] → Aggregated Results
"""

orchestrator_svc = restate.Service("Orchestrator")


example_prompt = (
    "Analyze the following text for sentiment, key points, and provide a summary:"
    "'Our Q3 results exceeded all expectations! Customer satisfaction reached 95%, "
    "revenue grew by 40% year-over-year, and we successfully launched three new product features. "
    "The team worked incredibly hard to deliver these outcomes despite supply chain challenges. "
    "Our market share increased to 23%, and we're well-positioned for continued growth in Q4.'"
)


class Prompt(BaseModel):
    message: str = example_prompt


@orchestrator_svc.handler()
async def process_text(ctx: restate.Context, prompt: Prompt) -> list[str]:
    """Orchestrate text analysis breakdown and parallel execution by specialized workers."""

    # Step 1: Orchestrator analyzes and breaks down the text analysis task
    task_breakdown = await ctx.run_typed(
        "orchestrator_analysis",
        llm_call,
        restate.RunOptions(max_attempts=3),
        system="""You are an orchestrator breaking down text analysis into specific subtasks.
        For each task, specify what the worker should focus on:
        [task_type]: [specific prompt/instructions for worker]""",
        prompt=f"Text to analyze: {prompt}",
    )

    # Parse the task breakdown
    worker_instructions = parse_instructions(task_breakdown)

    # Step 2: Workers execute their specialized tasks in parallel
    worker_tasks = []
    for task_type, instruction in worker_instructions.items():
        worker_task = ctx.run_typed(
            f"worker_{task_type.lower()}",
            llm_call,
            restate.RunOptions(max_attempts=3),
            system=f"You are a {task_type} specialist.",
            prompt=f"Task: {instruction} - Text to analyze: {prompt}",
        )
        worker_tasks.append((task_type, worker_task))

    # Wait for all workers to complete
    await restate.gather(*[task for _, task in worker_tasks])

    # Collect results
    return [f"{task_type} result: {await task}" for task_type, task in worker_tasks]
