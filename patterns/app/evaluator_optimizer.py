import restate
from pydantic import BaseModel
from util import llm_call, print_evaluation

"""
LLM Iterative Improvement

Generate → Evaluate → Improve loop until quality criteria are met.
Restate persists each iteration—if the process fails after 10 iterations,
it resumes from iteration 10, not from the beginning.

Generate → Evaluate → [Pass/Improve] → Final Result
"""

evaluator_optimizer = restate.Service("EvaluatorOptimizer")

example_prompt = (
    "Write a Python function that finds the longest palindromic substring in a string. "
    "It should be efficient and handle edge cases."
)


class Prompt(BaseModel):
    message: str = example_prompt


@evaluator_optimizer.handler()
async def improve_until_good(ctx: restate.Context, prompt: Prompt) -> str:
    """Iteratively improve a solution until it meets quality standards."""

    attempts: list[str] = []
    max_iterations = 5

    for iteration in range(max_iterations):
        # Generate solution (with context from previous attempts)
        context = ""
        if attempts:
            context = f"\nPrevious attempts that need improvement:\n" + "\n".join(
                f"- {a}" for a in attempts[-2:]
            )

        solution = await ctx.run_typed(
            f"generate_v{iteration+1}",
            llm_call,
            restate.RunOptions(max_attempts=3),
            system="Create a Python function to solve this task. Eagerly return results for review.",
            prompt=f" Previous attempts: {context} - Task: {prompt}" "",
        )

        # Evaluate the solution
        evaluation = await ctx.run_typed(
            f"evaluate_v{iteration+1}",
            llm_call,
            restate.RunOptions(max_attempts=3),
            prompt=f"""Evaluate this solution on correctness, efficiency, and readability.
            Reply with either:
            'PASS: [brief reason]' if the solution is correct and very well-implemented
            'IMPROVE: [specific issues to fix]' if it needs work

            Task: {prompt}
            Solution: {solution}""",
        )
        print_evaluation(iteration, solution, evaluation)

        if evaluation.startswith("PASS"):
            return solution

        # Store failed attempt for context
        attempts.append(solution)

    return f"Max iterations reached. Best attempt:\n{solution}"
