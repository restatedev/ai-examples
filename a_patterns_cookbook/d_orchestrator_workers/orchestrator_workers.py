import restate
from pydantic import BaseModel
from typing import Dict, List, Optional
from util.util import llm_call, extract_xml

"""
Orchestrator-worker pattern with Restate

This example demonstrates how to use Restate to implement an orchestrator that uses an LLM to compose a list of tasks,
and then run those tasks in parallel. Each of these tasks is a dedicated LLM call with a specific prompt.
Restate persists the outcomes of each of the LLM calls and makes sure the entire workflow runs to completion. 

This example is a translation of the Anthropic AI agents Python notebook examples:
https://github.com/anthropics/anthropic-cookbook/blob/main/patterns/agents/
"""

# Break down tasks and run them in parallel using worker LLMs.
flexible_orchestrator = restate.Service("FlexibleOrchestrator")


class OrchestrationRequest(BaseModel):
    orchestrator_prompt: str
    worker_prompt: str
    task: str
    llm_context: Optional[Dict] = None


@flexible_orchestrator.handler()
async def process(ctx: restate.ObjectContext, req: OrchestrationRequest) -> Dict:
    """Process task by breaking it down and running subtasks in parallel."""
    llm_context = req.llm_context or {}

    # Step 1: Get orchestrator response
    orchestrator_input = format_prompt(
        req.orchestrator_prompt, task=req.task, **llm_context
    )
    orchestrator_response = await ctx.run(
        "LLM call", lambda: llm_call(orchestrator_input)
    )

    # Parse orchestrator response
    analysis = extract_xml(orchestrator_response, "analysis")
    tasks_xml = extract_xml(orchestrator_response, "tasks")
    tasks = await ctx.run("parse tasks", lambda: parse_tasks(tasks_xml))

    print("\n=== ORCHESTRATOR OUTPUT ===")
    print(f"\nANALYSIS:\n{analysis}")
    print(f"\nTASKS:\n{tasks}")

    # Step 2: Process each task in parallel
    futures = [
        ctx.run(
            "process task",
            lambda task_info=task_info: llm_call(
                format_prompt(
                    req.worker_prompt,
                    original_task=req.task,
                    task_type=task_info["type"],
                    task_description=task_info["description"],
                    **llm_context,
                )
            ),
        )
        for task_info in tasks
    ]
    await restate.gather(*futures)
    worker_responses = [await future for future in futures]

    worker_results = [
        {
            "type": task_info["type"],
            "description": task_info["description"],
            "result": extract_xml(worker_response, "response"),
        }
        for worker_response, task_info in zip(worker_responses, tasks)
    ]

    return {
        "analysis": analysis,
        "worker_results": worker_results,
    }


# UTILS


def parse_tasks(tasks_xml: str) -> List[Dict]:
    """Parse XML tasks into a list of task dictionaries."""
    tasks = []
    current_task = {}

    for line in tasks_xml.split("\n"):
        line = line.strip()
        if not line:
            continue

        if line.startswith("<task>"):
            current_task = {}
        elif line.startswith("<type>"):
            current_task["type"] = line[6:-7].strip()
        elif line.startswith("<description>"):
            current_task["description"] = line[12:-13].strip()
        elif line.startswith("</task>"):
            if "description" in current_task:
                if "type" not in current_task:
                    current_task["type"] = "default"
                tasks.append(current_task)

    return tasks


def format_prompt(template: str, **kwargs) -> str:
    """Format a prompt template with variables."""
    try:
        return template.format(**kwargs)
    except KeyError as e:
        raise ValueError(f"Missing required prompt variable: {e}")
