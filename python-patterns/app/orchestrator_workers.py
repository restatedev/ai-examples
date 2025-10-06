import restate
from litellm.types.utils import ModelResponse

from pydantic import BaseModel, RootModel
from restate import RunOptions

from .util.litellm_call import llm_call

import litellm

"""
Orchestrator-Worker Pattern

Break down complex tasks into specialized subtasks and execute them in parallel.
If any worker fails, Restate retries only that worker while preserving other completed work.

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

class Task(BaseModel):
    task_type: str
    instruction: str

class TaskList(BaseModel):
    tasks: list[Task]

@orchestrator_svc.handler()
async def process_text(ctx: restate.Context, prompt: Prompt) -> list[str]:
    """Orchestrate text analysis breakdown and parallel execution by specialized workers."""

    messages = [
        {"role": "system",
         "content": "You are an orchestrator that breaks down text analysis tasks into specialized subtasks for workers."},
        {"role": "user", "content": f"Text to analyze: {prompt.message}"}
    ]

    # Step 1: Orchestrator analyzes and breaks down the text analysis task
    litellm.enable_json_schema_validation = True
    response = await ctx.run_typed(
        "orchestrator_analysis",
        litellm.completion,
        RunOptions(max_attempts=3, type_hint=ModelResponse),
        model="gpt-4o",
        messages=messages,
        response_format=TaskList
    )
    task_list_json = response.choices[0].message.content
    task_list = TaskList.model_validate_json(task_list_json)

    # Step 2: Workers execute their specialized tasks in parallel
    worker_tasks = []
    for task in task_list.tasks:
        worker_task = ctx.run_typed(
            task.task_type,
            llm_call,
            restate.RunOptions(max_attempts=3),
            system=f"You are a {task.task_type} specialist.",
            prompt=f"Task: {task.instruction} - Text to analyze: {prompt}",
        )
        worker_tasks.append({"task_type": task.task_type, "task_promise": worker_task})

    # Wait for all workers to complete
    await restate.gather(*[task["task_promise"] for task in worker_tasks])

    # Collect results
    return [f"{task["task_type"]} result: {await task["task_promise"]}" for task in worker_tasks]
