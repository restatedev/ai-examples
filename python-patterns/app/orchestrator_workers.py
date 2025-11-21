"""
Orchestrator-Worker Pattern

Break down complex tasks into specialized subtasks and execute them in parallel.
If any worker fails, Restate retries only that worker while preserving other completed work.

Task → Orchestrator → [Worker A, Worker B, Worker C] → Aggregated Results
"""

import litellm
import restate

from pydantic import BaseModel
from restate import RunOptions

from .util.litellm_call import llm_call
from .util.util import parse_task_list, TaskList

litellm.enable_json_schema_validation = True

example_prompt = """Analyze the following text for sentiment, key points, and provide a summary:
'Our Q3 results exceeded all expectations! Customer satisfaction reached 95%, 
revenue grew by 40% year-over-year, and we successfully launched three new product features. 
The team worked incredibly hard to deliver these outcomes despite supply chain challenges. 
Our market share increased to 23%, and we're well-positioned for continued growth in Q4.'"""


class Prompt(BaseModel):
    message: str = example_prompt


orchestrator_svc = restate.Service("Orchestrator")


@orchestrator_svc.handler()
async def process(ctx: restate.Context, prompt: Prompt) -> str:
    """Orchestrate text analysis breakdown and parallel execution by specialized workers."""

    # Step 1: Orchestrator analyzes and breaks down the text analysis task
    async def generate_task_list() -> TaskList:
        content = f"""You are an orchestrator that breaks down text analysis tasks into specialized subtasks for workers.
        Analyze the following text: {prompt.message}"""
        resp = await litellm.acompletion(
            model="gpt-4o",
            messages=[{"role": "user", "content": content}],
            response_format=TaskList,
        )
        return parse_task_list(resp)

    response = await ctx.run_typed(
        "orchestrator_analysis",
        generate_task_list,  # Use your preferred LLM SDK here
        RunOptions(max_attempts=3),
    )

    # Step 2: Workers execute their specialized tasks in parallel
    task_promises = []
    for task in response.tasks:
        worker_task = ctx.run_typed(
            task.task_type,
            llm_call,  # Use your preferred LLM SDK here
            RunOptions(max_attempts=3),
            messages=f"""You are a {task.task_type} specialist."
            Task: {task.instruction} - Text to analyze: {prompt}""",
        )
        task_promises.append(worker_task)

    # Wait for all workers to complete
    await restate.gather(*task_promises)

    # Collect results
    results = [
        f"{task.task_type} result: {(await task_promise).content}"
        for task, task_promise in zip(response.tasks, task_promises)
    ]
    return "\n\n--".join(results)
