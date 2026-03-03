import json

import restate
from google.adk import Runner
from google.adk.agents.llm_agent import Agent
from google.adk.apps import App
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, Part
from pydantic import BaseModel
from restate.ext.adk import RestatePlugin


class ResearchTask(BaseModel):
    question: str
    session_id: str = "research"


class ReportRequest(BaseModel):
    topic: str = "The impact of renewable energy on global economies"


async def run_agent(runner: Runner, user_id: str, session_id: str, message: str) -> str:
    """Run an ADK agent and return the final text response."""
    events = runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=Content(role="user", parts=[Part.from_text(text=message)]),
    )
    final_response = ""
    async for event in events:
        if event.is_final_response() and event.content and event.content.parts:
            if event.content.parts[0].text:
                final_response = event.content.parts[0].text
    return final_response


# <start_here>
APP_NAME = "research"

planner = Agent(
    model="gemini-2.5-flash",
    name="research_planner",
    instruction="""You are a research planner. Break the topic into 2-4 research
    sub-tasks. Respond with a JSON array of strings, each a specific
    research question. Example: ["question 1", "question 2"]""",
)

researcher = Agent(
    model="gemini-2.5-flash",
    name="researcher",
    instruction="You are a research assistant. Provide a concise, factual answer.",
)

writer = Agent(
    model="gemini-2.5-flash",
    name="report_writer",
    instruction="You are a report writer. Combine the research findings into a cohesive report.",
)

report_service = restate.Service("ResearchReport")


@report_service.handler()
async def generate(ctx: restate.Context, req: ReportRequest) -> dict:
    # Step 1: Orchestrator creates a research plan
    plan_app = App(name=APP_NAME, root_agent=planner, plugins=[RestatePlugin()])
    plan_runner = Runner(app=plan_app, session_service=InMemorySessionService())
    plan_output = await run_agent(plan_runner, "user", "plan", req.topic)
    tasks = json.loads(plan_output)

    # Step 2: Dispatch workers in parallel
    worker_promises = []
    for task in tasks:
        promise = ctx.service_call(run_researcher, ResearchTask(question=task))
        worker_promises.append(promise)

    await restate.gather(*worker_promises)
    findings = [await p for p in worker_promises]

    # Step 3: Combine results into a report
    writer_app = App(name=APP_NAME, root_agent=writer, plugins=[RestatePlugin()])
    writer_runner = Runner(app=writer_app, session_service=InMemorySessionService())
    report = await run_agent(
        writer_runner, "user", "report",
        f"Topic: {req.topic}\n\nResearch findings:\n{json.dumps(findings, indent=2)}",
    )

    return {"report": report, "task_count": len(tasks)}


researcher_service = restate.Service("Researcher")


@researcher_service.handler()
async def run_researcher(ctx: restate.Context, task: ResearchTask) -> str:
    res_app = App(name=APP_NAME, root_agent=researcher, plugins=[RestatePlugin()])
    res_runner = Runner(app=res_app, session_service=InMemorySessionService())
    return await run_agent(res_runner, "user", task.session_id, task.question)
# <end_here>


if __name__ == "__main__":
    import hypercorn
    import asyncio

    app = restate.app(services=[report_service, researcher_service])
    conf = hypercorn.Config()
    conf.bind = ["0.0.0.0:9080"]
    asyncio.run(hypercorn.asyncio.serve(app, conf))
