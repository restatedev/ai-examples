"""
Evaluator-Optimizer Pattern

Generate → Evaluate → Improve loop until quality criteria are met.
Restate persists each iteration, resuming from the last completed step on failure.

Generate → Evaluate → [Pass/Improve] → Final Result
"""

import restate
from pydantic import BaseModel
from restate import RunOptions

from .util.litellm_call import llm_call
from .util.util import print_evaluation

max_iterations = 5

example_prompt = """Write a Python function that finds the longest palindromic substring in a string. 
It should be efficient and handle edge cases."""

evaluation_prompt = """Evaluate this solution on correctness, efficiency, and readability. 
            Reply with either:
            'PASS: [brief reason]' if the solution is correct and very well-implemented
            'IMPROVE: [specific issues to fix]' if it needs work"""


class Task(BaseModel):
    message: str = example_prompt


evaluator_optimizer = restate.Service("EvaluatorOptimizer")


@evaluator_optimizer.handler()
async def improve_until_good(ctx: restate.Context, task: Task) -> str | None:
    """Iteratively improve a solution until it meets quality standards."""

    solution: str | None = None
    attempts: list[str] = []

    for iteration in range(max_iterations):
        # Generate solution (with context from previous attempts)
        solution_response = await ctx.run_typed(
            f"generate_v{iteration+1}",
            llm_call,  # Use your preferred LLM SDK here
            RunOptions(max_attempts=3),
            prompt=f"Task: {task} - Previous attempts: {attempts}",
        )
        solution = solution_response.content
        if solution is not None:
            attempts.append(solution)

        # Evaluate the solution
        evaluation_response = await ctx.run_typed(
            f"evaluate_v{iteration+1}",
            llm_call,
            RunOptions(max_attempts=3),
            system=evaluation_prompt,
            prompt=f"Task: {task} - Solution: {solution}" "",
        )
        evaluation = evaluation_response.content
        print_evaluation(iteration, solution, evaluation)

        if evaluation and evaluation.startswith("PASS"):
            return solution

    return f"Max iterations reached. Best attempt:\n {solution}"
