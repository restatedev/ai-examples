import restate
from pydantic_ai import Agent
from pydantic import BaseModel
from restate.ext.pydantic import RestateAgent


class CodeRequest(BaseModel):
    task: str = "Write a function that checks if a string is a palindrome"


# <start_here>
generator = Agent(
    "openai:gpt-4o-mini",
    system_prompt="You are a code generator. Write clean, correct code.",
)
restate_generator = RestateAgent(generator)

evaluator = Agent(
    "openai:gpt-4o-mini",
    system_prompt="""You are a code reviewer. Evaluate the code for correctness,
    readability, and edge cases. Respond with PASS if acceptable,
    or FAIL: <feedback> with specific issues to fix.""",
)
restate_evaluator = RestateAgent(evaluator)

code_service = restate.Service("CodeGenerator")


@code_service.handler()
async def generate(_ctx: restate.Context, req: CodeRequest) -> dict:
    feedback = ""
    max_iterations = 3

    for i in range(max_iterations):
        # Step 1: Generate code
        prompt = (
            f"Task: {req.task}\n\nPrevious attempt was rejected:\n{feedback}\n\nPlease fix the issues."
            if feedback
            else f"Task: {req.task}"
        )
        gen_result = await restate_generator.run(prompt)
        code = gen_result.output

        # Step 2: Evaluate the code
        eval_result = await restate_evaluator.run(f"Task: {req.task}\n\nCode:\n{code}")
        evaluation = eval_result.output

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
