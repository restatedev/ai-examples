import restate
from google.adk import Runner
from google.adk.agents.llm_agent import Agent
from google.adk.apps import App
from google.genai.types import Content, Part
from pydantic import BaseModel
from restate.ext.adk import RestatePlugin, RestateSessionService

from utils.utils import parse_agent_response


class CodeRequest(BaseModel):
    task: str = "Write a function that checks if a string is a palindrome"


async def run_agent(runner: Runner, user_id: str, session_id: str, message: str) -> str:
    """Run an ADK agent and return the final text response."""
    events = runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=Content(role="user", parts=[Part.from_text(text=message)]),
    )
    return await parse_agent_response(events)


# <start_here>
APP_NAME = "codegen"

generator = Agent(
    model="gemini-2.5-flash",
    name="code_generator",
    instruction="You are a code generator. Write clean, correct code.",
)

evaluator = Agent(
    model="gemini-2.5-flash",
    name="code_evaluator",
    instruction="""You are a code reviewer. Evaluate the code for correctness,
    readability, and edge cases. Respond with PASS if acceptable,
    or FAIL: <feedback> with specific issues to fix.""",
)

code_service = restate.VirtualObject("CodeGenerator")


@code_service.handler()
async def generate(ctx: restate.ObjectContext, req: CodeRequest) -> dict:
    feedback = ""
    max_iterations = 3

    for i in range(max_iterations):
        # Step 1: Generate code
        prompt = (
            f"Task: {req.task}\n\nPrevious attempt was rejected:\n{feedback}\n\nPlease fix the issues."
            if feedback
            else f"Task: {req.task}"
        )
        gen_app = App(name=APP_NAME, root_agent=generator, plugins=[RestatePlugin()])
        gen_runner = Runner(app=gen_app, session_service=RestateSessionService())
        code = await run_agent(gen_runner, "user", f"gen-{i}", prompt)

        # Step 2: Evaluate the code
        eval_app = App(name=APP_NAME, root_agent=evaluator, plugins=[RestatePlugin()])
        eval_runner = Runner(app=eval_app, session_service=RestateSessionService())
        evaluation = await run_agent(eval_runner, "user", f"eval-{i}", f"Task: {req.task}\n\nCode:\n{code}")

        if evaluation.startswith("PASS"):
            return {"code": code, "iterations": i + 1}

        feedback = evaluation

    return {"code": "Max iterations reached", "iterations": max_iterations}
# <end_here>


if __name__ == "__main__":
    import hypercorn
    import asyncio

    restate_app = restate.app(services=[code_service])
    conf = hypercorn.Config()
    conf.bind = ["0.0.0.0:9080"]
    asyncio.run(hypercorn.asyncio.serve(restate_app, conf))
