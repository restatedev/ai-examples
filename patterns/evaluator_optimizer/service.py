import restate
from util import llm_call

"""
LLM Iterative Improvement

Generate → Evaluate → Improve loop until quality criteria are met.
Restate persists each iteration—if the process fails after 10 iterations,
it resumes from iteration 10, not from the beginning.

Generate → Evaluate → [Pass/Improve] → Final Result
"""

evaluator_optimizer = restate.Service("EvaluatorOptimizer")

@evaluator_optimizer.handler()
async def improve_until_good(ctx: restate.Context, task: str) -> str:
    """Iteratively improve a solution until it meets quality standards."""

    attempts = []
    max_iterations = 5

    for iteration in range(max_iterations):
        # Generate solution (with context from previous attempts)
        context = ""
        if attempts:
            context = f"\nPrevious attempts that need improvement:\n" + "\n".join(f"- {a}" for a in attempts[-2:])

        solution = await ctx.run(
            f"generate_v{iteration+1}",
            lambda: llm_call(f"""Create a Python function to solve this task.
            Focus on correctness, efficiency, and readability.
            {context}

            Task: {task}""")
        )

        # Evaluate the solution
        evaluation = await ctx.run(
            f"evaluate_v{iteration+1}",
            lambda: llm_call(f"""Evaluate this solution. Reply with either:
            'PASS: [brief reason]' if the solution is correct and well-implemented
            'IMPROVE: [specific issues to fix]' if it needs work

            Task: {task}
            Solution: {solution}""")
        )

        print(f"Iteration {iteration+1}:")
        print(f"Solution: {solution[:100]}...")
        print(f"Evaluation: {evaluation}")
        print("-" * 50)

        if evaluation.startswith("PASS"):
            return solution

        # Store failed attempt for context
        attempts.append(solution)

    return f"Max iterations reached. Best attempt:\n{solution}"