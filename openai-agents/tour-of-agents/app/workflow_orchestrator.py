import json

import restate
from agents import Agent
from pydantic import BaseModel
from restate.ext.openai import DurableRunner


class ReportRequest(BaseModel):
    topic: str = "The impact of renewable energy on global economies"


class ResearchTask(BaseModel):
    question: str


class TaskList(BaseModel):
    tasks: list[ResearchTask]


# <start_here>
planner = Agent(
    name="ResearchPlanner",
    instructions="You are a research planner. Break the topic into 2-4 research sub-tasks.",
    output_type=TaskList,
)

researcher = Agent(
    name="Researcher",
    instructions="You are a research assistant. Provide a concise, factual answer.",
)

writer = Agent(
    name="ReportWriter",
    instructions="You are a report writer. Combine the research findings into a cohesive report.",
)

report_service = restate.Service("ResearchReport")


@report_service.handler()
async def generate(ctx: restate.Context, req: ReportRequest) -> dict:
    # Step 1: Orchestrator creates a research plan
    plan_result = await DurableRunner.run(planner, req.topic)
    tasks = plan_result.final_output.tasks

    # Step 2: Dispatch workers in parallel
    worker_promises = []
    for task in tasks:
        promise = ctx.service_call(run_researcher, task)
        worker_promises.append(promise)

    await restate.gather(*worker_promises)
    findings = [await p for p in worker_promises]

    # Step 3: Combine results into a report
    report_result = await DurableRunner.run(
        writer,
        f"Topic: {req.topic}\n\nResearch findings:\n{json.dumps(findings, indent=2)}",
    )

    return {"report": report_result.final_output, "task_count": len(tasks)}


researcher_service = restate.Service("Researcher")


@researcher_service.handler()
async def run_researcher(ctx: restate.Context, task: ResearchTask) -> str:
    result = await DurableRunner.run(researcher, task.question)
    return result.final_output


# <end_here>


if __name__ == "__main__":
    import hypercorn
    import asyncio

    app = restate.app(services=[report_service, researcher_service])
    conf = hypercorn.Config()
    conf.bind = ["0.0.0.0:9080"]
    asyncio.run(hypercorn.asyncio.serve(app, conf))
