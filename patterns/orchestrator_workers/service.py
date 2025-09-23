import restate
from util.util import llm_call

"""
LLM Orchestrator-Workers

Break down complex tasks into specialized subtasks and execute them in parallel.
If any worker fails, Restate retries only that worker—other completed work is preserved.

Task → Orchestrator → [Worker A, Worker B, Worker C] → Aggregated Results
"""

orchestrator_svc = restate.Service("Orchestrator")

@orchestrator_svc.handler()
async def process_task(ctx: restate.Context, task: str) -> dict:
    """Orchestrate task breakdown and parallel execution by specialized workers."""

    # Step 1: Orchestrator analyzes and breaks down the task
    breakdown = await ctx.run(
        "orchestrator_analysis",
        lambda: llm_call(f"""Break down this task into 3 different approaches:
        1. Technical approach (detailed, precise)
        2. Creative approach (engaging, story-driven)
        3. Practical approach (actionable, step-by-step)

        Return exactly 3 approaches, one per line:
        TECHNICAL: [description]
        CREATIVE: [description]
        PRACTICAL: [description]

        Task: {task}""")
    )

    # Parse the approaches
    approaches = []
    for line in breakdown.strip().split('\n'):
        if ':' in line:
            approach_type, description = line.split(':', 1)
            approaches.append({
                'type': approach_type.strip(),
                'description': description.strip()
            })

    print(f"Orchestrator identified {len(approaches)} approaches:")
    for approach in approaches:
        print(f"- {approach['type']}: {approach['description']}")

    # Step 2: Workers execute approaches in parallel
    worker_tasks = []
    for i, approach in enumerate(approaches):
        worker_task = ctx.run(
            f"worker_{approach['type'].lower()}",
            lambda approach=approach: llm_call(f"""Execute this approach for the given task.
            Approach: {approach['description']}
            Focus on delivering a complete solution in this style.

            Original task: {task}""")
        )
        worker_tasks.append(worker_task)

    # Wait for all workers to complete
    await restate.gather(*worker_tasks)
    results = [await task for task in worker_tasks]

    # Combine results
    worker_outputs = []
    for approach, result in zip(approaches, results):
        worker_outputs.append({
            'approach': approach['type'],
            'description': approach['description'],
            'result': result
        })

    return {
        'task': task,
        'approaches_identified': len(approaches),
        'worker_results': worker_outputs
    }