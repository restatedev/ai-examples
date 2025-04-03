import restate
from pydantic import BaseModel
from typing import Dict, List, Optional
from util import llm_call, extract_xml


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
        orchestrator_prompt=req.orchestrator_prompt, task=req.task, **llm_context
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

    # Step 2: Process each task
    worker_results = []
    for task_info in tasks:
        worker_input = format_prompt(
            req.worker_prompt,
            original_task=req.task,
            task_type=task_info["type"],
            task_description=task_info["description"],
            **llm_context,
        )

        worker_response = await ctx.run("process task", lambda: llm_call(worker_input))
        result = extract_xml(worker_response, "response")

        worker_results.append(
            {
                "type": task_info["type"],
                "description": task_info["description"],
                "result": result,
            }
        )
        # Expose the state to the outside
        ctx.set("worker_results", worker_results)

        print(f"\n=== WORKER RESULT ({task_info['type']}) ===\n{result}\n")

    return {
        "analysis": analysis,
        "worker_results": worker_results,
    }


app = restate.app(services=[flexible_orchestrator])
