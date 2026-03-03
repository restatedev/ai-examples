import restate
from agents import Agent
from pydantic import BaseModel
from restate.ext.openai import DurableRunner


class CodeRequest(BaseModel):
    task: str = "Write a function that checks if a string is a palindrome"


# <start_here>
generator = Agent(
    name="CodeGenerator",
    instructions="You are a code generator. Write clean, correct code.",
)

evaluator = Agent(
    name="CodeEvaluator",
    instructions="""You are a code reviewer. Evaluate the code for correctness,
    readability, and edge cases. Respond with PASS if acceptable,
    or FAIL: <feedback> with specific issues to fix.""",
)

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
        gen_result = await DurableRunner.run(generator, prompt)
        code = gen_result.final_output

        # Step 2: Evaluate the code
        eval_result = await DurableRunner.run(
            evaluator, f"Task: {req.task}\n\nCode:\n{code}"
        )
        evaluation = eval_result.final_output

        if evaluation.startswith("PASS"):
            return {"code": code, "iterations": i + 1}

        feedback = evaluation

    return {"code": "Max iterations reached", "iterations": max_iterations}


# <end_here>


if __name__ == "__main__":
    import hypercorn
    import asyncio

    app = restate.app(services=[code_service])
    conf = hypercorn.Config()
    conf.bind = ["0.0.0.0:9080"]
    asyncio.run(hypercorn.asyncio.serve(app, conf))
