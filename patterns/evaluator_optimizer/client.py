import httpx

def main():
    task = "Write a Python function that finds the longest palindromic substring in a string. It should be efficient and handle edge cases."

    print(f"Task: {task}")
    print("=" * 60)

    r = httpx.post(
        "http://localhost:8080/EvaluatorOptimizer/improve_until_good",
        json=task,
        timeout=120,
    )
    r.raise_for_status()

    print("\nFinal Solution:")
    print("-" * 40)
    print(r.json())

if __name__ == "__main__":
    main()


"""
This example demonstrates iterative improvement with Restate fault tolerance:

Iteration 1: Generate initial solution → Evaluate → May need improvement
Iteration 2: Improve based on feedback → Evaluate → May need improvement
Iteration 3: Further refinement → Evaluate → PASS (or continue)

If the process crashes at iteration 3, Restate resumes from iteration 3,
preserving all previous work and context.
"""