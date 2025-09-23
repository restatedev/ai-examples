import httpx
import json

def main():
    task = "Create a comprehensive guide for remote team collaboration"

    print(f"Task: {task}")
    print("=" * 60)

    r = httpx.post(
        "http://localhost:8080/Orchestrator/process_task",
        json=task,
        timeout=180,
    )
    r.raise_for_status()

    result = r.json()

    print(f"\nOrchestrator identified {result['approaches_identified']} approaches:")
    print("-" * 50)

    for i, worker_result in enumerate(result['worker_results'], 1):
        print(f"\nApproach {i}: {worker_result['approach']}")
        print(f"Description: {worker_result['description']}")
        print(f"Result: {worker_result['result'][:200]}...")
        print("-" * 50)

if __name__ == "__main__":
    main()


"""
This example demonstrates orchestrator-worker pattern with parallel execution:

1. Orchestrator breaks down the task into 3 specialized approaches
2. Workers execute each approach in parallel (Technical, Creative, Practical)
3. Results are aggregated into a comprehensive solution

If Worker B fails, Restate retries only Worker B while preserving
the completed work from Workers A and C.
"""