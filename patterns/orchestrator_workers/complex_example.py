import httpx
import json

# Complex tasks that benefit from multiple approaches
complex_tasks = [
    "Develop a complete marketing strategy for launching a new SaaS product",
    "Design a comprehensive employee onboarding program for a tech startup",
    "Create a disaster recovery plan for a small business"
]

def main():
    for i, task in enumerate(complex_tasks, 1):
        print(f"\n{'='*70}")
        print(f"Complex Task {i}: {task}")
        print('='*70)

        r = httpx.post(
            "http://localhost:8080/Orchestrator/process_task",
            json=task,
            timeout=300,
        )
        r.raise_for_status()

        result = r.json()

        print(f"\nOrchestrator Analysis: {result['approaches_identified']} approaches identified")

        for worker_result in result['worker_results']:
            print(f"\n--- {worker_result['approach']} Approach ---")
            print(f"Focus: {worker_result['description']}")
            # Show first 300 chars of result
            result_preview = worker_result['result'][:300]
            print(f"Output: {result_preview}{'...' if len(worker_result['result']) > 300 else ''}")

if __name__ == "__main__":
    main()


"""
These complex examples showcase the orchestrator-worker pattern's strength:

- Each task is analyzed once by the orchestrator
- Multiple specialized workers tackle different aspects simultaneously
- Comprehensive solutions emerge from diverse approaches
- Fault tolerance: individual worker failures don't impact others

This demonstrates Restate's power in coordinating complex, multi-faceted LLM workflows.
"""