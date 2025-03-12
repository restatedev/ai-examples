from typing import Dict, List, Optional
from util import llm_call, extract_xml

def parse_tasks(tasks_xml: str) -> List[Dict]:
    """Parse XML tasks into a list of task dictionaries."""
    tasks = []
    current_task = {}

    for line in tasks_xml.split('\n'):
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

class FlexibleOrchestrator:
    """Break down tasks and run them in parallel using worker LLMs."""

    def __init__(
            self,
            orchestrator_prompt: str,
            worker_prompt: str,
    ):
        """Initialize with prompt templates."""
        self.orchestrator_prompt = orchestrator_prompt
        self.worker_prompt = worker_prompt

    def _format_prompt(self, template: str, **kwargs) -> str:
        """Format a prompt template with variables."""
        try:
            return template.format(**kwargs)
        except KeyError as e:
            raise ValueError(f"Missing required prompt variable: {e}")

    def process(self, task: str, context: Optional[Dict] = None) -> Dict:
        """Process task by breaking it down and running subtasks in parallel."""
        context = context or {}

        # Step 1: Get orchestrator response
        orchestrator_input = self._format_prompt(
            self.orchestrator_prompt,
            task=task,
            **context
        )
        orchestrator_response = llm_call(orchestrator_input)

        # Parse orchestrator response
        analysis = extract_xml(orchestrator_response, "analysis")
        tasks_xml = extract_xml(orchestrator_response, "tasks")
        tasks = parse_tasks(tasks_xml)

        print("\n=== ORCHESTRATOR OUTPUT ===")
        print(f"\nANALYSIS:\n{analysis}")
        print(f"\nTASKS:\n{tasks}")

        # Step 2: Process each task
        worker_results = []
        for task_info in tasks:
            worker_input = self._format_prompt(
                self.worker_prompt,
                original_task=task,
                task_type=task_info['type'],
                task_description=task_info['description'],
                **context
            )

            worker_response = llm_call(worker_input)
            result = extract_xml(worker_response, "response")

            worker_results.append({
                "type": task_info["type"],
                "description": task_info["description"],
                "result": result
            })

            print(f"\n=== WORKER RESULT ({task_info['type']}) ===\n{result}\n")

        return {
            "analysis": analysis,
            "worker_results": worker_results,
        }