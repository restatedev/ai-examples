import json

import restate
from google.adk import Runner
from google.adk.agents.llm_agent import Agent
from google.adk.apps import App
from google.genai.types import Content, Part
from pydantic import BaseModel
from restate.ext.adk import RestatePlugin, RestateSessionService

from utils.utils import parse_agent_response


class ResearchTask(BaseModel):
    question: str


class ReportRequest(BaseModel):
    topic: str = "The impact of renewable energy on global economies"


APP_NAME = "agents"

# AGENTS
planner = Agent(
    model="gemini-2.5-flash",
    name="research_planner",
    instruction="""You are a research planner. Break the topic into 2-4 research
    sub-tasks. Respond with a JSON array of strings, each a specific
    research question. Example: ["question 1", "question 2"]""",
)
plan_app = App(name=APP_NAME, root_agent=planner, plugins=[RestatePlugin()])
plan_runner = Runner(app=plan_app, session_service=RestateSessionService())

researcher = Agent(
    model="gemini-2.5-flash",
    name="researcher",
    instruction="You are a research assistant. Provide a concise, factual answer.",
)
research_app = App(name=APP_NAME, root_agent=researcher, plugins=[RestatePlugin()])
research_runner = Runner(app=research_app, session_service=RestateSessionService())

writer = Agent(
    model="gemini-2.5-flash",
    name="report_writer",
    instruction="You are a report writer. Combine the research findings into a cohesive report.",
)
writer_app = App(name=APP_NAME, root_agent=writer, plugins=[RestatePlugin()])
writer_runner = Runner(app=writer_app, session_service=RestateSessionService())

# AGENT SERVICE
# <start_here>
report_service = restate.VirtualObject("ResearchReport")


@report_service.handler()
async def generate(ctx: restate.ObjectContext, req: ReportRequest) -> dict:
    session_id = str(ctx.uuid())
    # Step 1: Orchestrator creates a research plan
    plan_events = plan_runner.run_async(
        user_id=ctx.key(),
        session_id=session_id,
        new_message=Content(role="user", parts=[Part.from_text(text=req.topic)]),
    )
    plan_output =  await parse_agent_response(plan_events)
    tasks = json.loads(plan_output)

    # Step 2: Dispatch workers in parallel
    worker_promises = []
    for task in tasks:
        promise = ctx.service_call(run_researcher, ResearchTask(question=task))
        worker_promises.append(promise)

    await restate.gather(*worker_promises)
    findings = [await p for p in worker_promises]

    # Step 3: Combine results into a report
    results = f"Topic: {req.topic}\n\nResearch findings:\n{json.dumps(findings, indent=2)}"
    events = writer_runner.run_async(
        user_id=ctx.key(),
        session_id=session_id,
        new_message=Content(role="user", parts=[Part.from_text(text=results)]),
    )
    report = await parse_agent_response(events)

    return {"report": report, "task_count": len(tasks)}


researcher_service = restate.VirtualObject("Researcher")


@researcher_service.handler()
async def run_researcher(ctx: restate.ObjectContext, task: ResearchTask) -> str:
    events = research_runner.run_async(
        user_id=ctx.key(),
        session_id=str(ctx.uuid()),
        new_message=Content(role="user", parts=[Part.from_text(text=task.question)]),
    )
    return await parse_agent_response(events)
# <end_here>


if __name__ == "__main__":
    import hypercorn
    import asyncio

    restate_app = restate.app(services=[report_service, researcher_service])
    conf = hypercorn.Config()
    conf.bind = ["0.0.0.0:9080"]
    asyncio.run(hypercorn.asyncio.serve(restate_app, conf))
