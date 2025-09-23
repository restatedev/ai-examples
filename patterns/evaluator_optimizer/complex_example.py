import httpx

# More complex tasks that typically require multiple iterations
complex_tasks = [
    "Implement a MinStack class with push, pop, and getMin operations all in O(1) time complexity.",
    "Write a function to detect cycles in a linked list and return the node where the cycle begins.",
    "Create a thread-safe singleton pattern in Python with lazy initialization."
]

def main():
    for i, task in enumerate(complex_tasks, 1):
        print(f"\n{'='*60}")
        print(f"Complex Task {i}: {task}")
        print('='*60)

        r = httpx.post(
            "http://localhost:8080/EvaluatorOptimizer/improve_until_good",
            json=task,
            timeout=180,
        )
        r.raise_for_status()

        print("\nFinal Solution:")
        print("-" * 40)
        solution = r.json()
        print(solution[:500] + "..." if len(solution) > 500 else solution)

if __name__ == "__main__":
    main()


"""
These complex examples often require multiple iterations:
- Initial solution may have bugs or inefficiencies
- Evaluator identifies issues (edge cases, complexity, thread safety)
- Generator improves based on specific feedback
- Process continues until all criteria are met

Restate ensures no iteration work is lost even if the improvement process
takes a long time or encounters failures.
"""