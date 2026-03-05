"""
Evaluator-Optimizer Pattern

Generate → Evaluate → Improve loop until quality criteria are met.
Restate persists each iteration, resuming from the last completed step on failure.
"""

import restate
from pydantic import BaseModel
from restate import RunOptions

from .util.litellm_call import llm_call


class CodeRequest(BaseModel):
    task: str = "Write a function that checks if a string is a palindrome"


# <start_here>
code_service = restate.Service("CodeGenerator")


@code_service.handler()
async def generate(ctx: restate.Context, req: CodeRequest) -> dict:
    feedback = ""
    max_iterations = 3

    for i in range(max_iterations):
        # Step 1: Generate code
        prompt = (
            f"Task: {req.task}\n\nPrevious attempt was rejected:\n{feedback}\n\nPlease fix the issues."
            if feedback
            else f"Task: {req.task}"
        )
        code = await ctx.run_typed(
            f"Generate code (attempt {i + 1})", llm_call,
            RunOptions(max_attempts=3),
            messages=prompt,
            system="You are a code generator. Write clean, correct code.",
        )

        # Step 2: Evaluate the code
        evaluation = await ctx.run_typed(
            f"Evaluate code (attempt {i + 1})", llm_call,
            RunOptions(max_attempts=3),
            messages=f"Task: {req.task}\n\nCode:\n{code.content}",
            system="""You are a code reviewer. Evaluate the code for correctness,
            readability, and edge cases. Respond with PASS if acceptable,
            or FAIL: <feedback> with specific issues to fix.""",
        )

        if evaluation.content.startswith("PASS"):
            return {"code": code.content, "iterations": i + 1}

        feedback = evaluation.content

    return {"code": "Max iterations reached", "iterations": max_iterations}
# <end_here>
