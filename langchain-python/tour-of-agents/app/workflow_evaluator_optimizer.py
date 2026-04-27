"""Generator/evaluator loop: a writer agent and a reviewer agent iterate
until the reviewer says PASS or we hit the iteration cap."""

import restate
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model

from restate.ext.langchain import RestateMiddleware

from utils.models import CodeRequest


# <start_here>
generator = create_agent(
    model=init_chat_model("openai:gpt-4o-mini"),
    tools=[],
    system_prompt="You are a code generator. Write clean, correct code.",
    middleware=[RestateMiddleware()],
)

evaluator = create_agent(
    model=init_chat_model("openai:gpt-4o-mini"),
    tools=[],
    system_prompt=(
        "You are a code reviewer. Evaluate the code for correctness, "
        "readability, and edge cases. Respond with PASS if acceptable, or "
        "FAIL: <feedback> with specific issues to fix."
    ),
    middleware=[RestateMiddleware()],
)

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
        gen_result = await generator.ainvoke({"messages": [{"role": "user", "content": prompt}]})
        code = gen_result["messages"][-1].content

        # Step 2: Evaluate the code
        eval_result = await evaluator.ainvoke(
            {"messages": [{"role": "user", "content": f"Task: {req.task}\n\nCode:\n{code}"}]}
        )
        evaluation = eval_result["messages"][-1].content

        if evaluation.startswith("PASS"):
            return {"code": code, "iterations": i + 1}

        feedback = evaluation

    return {"code": "Max iterations reached", "iterations": max_iterations}


# <end_here>


if __name__ == "__main__":
    import asyncio

    import hypercorn
    import hypercorn.asyncio

    app = restate.app(services=[code_service])
    conf = hypercorn.Config()
    conf.bind = ["0.0.0.0:9080"]
    asyncio.run(hypercorn.asyncio.serve(app, conf))
