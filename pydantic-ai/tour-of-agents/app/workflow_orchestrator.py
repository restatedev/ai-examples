import json

import restate
from pydantic_ai import Agent
from pydantic import BaseModel
from restate.ext.pydantic import RestateAgent


class ResearchTask(BaseModel):
    question: str


class ReportRequest(BaseModel):
    topic: str = "The impact of renewable energy on global economies"


class TaskList(BaseModel):
    tasks: list[ResearchTask]


# <start_here>
planner = Agent(
    "openai:gpt-4o-mini",
    system_prompt="You are a research planner. Break the topic into 2-4 research sub-tasks.",
    output_type=TaskList,
)
restate_planner = RestateAgent(planner)

researcher = Agent(
    "openai:gpt-4o-mini",
    system_prompt="You are a research assistant. Provide a concise, factual answer.",
)
restate_researcher = RestateAgent(researcher)

writer = Agent(
    "openai:gpt-4o-mini",
    system_prompt="You are a report writer. Combine the research findings into a cohesive report.",
)
restate_writer = RestateAgent(writer)

report_service = restate.Service("ResearchReport")


@report_service.handler()
async def generate(ctx: restate.Context, req: ReportRequest) -> dict:
    # Step 1: Orchestrator creates a research plan
    plan_result = await restate_planner.run(req.topic)
    tasks = plan_result.output.tasks

    # Step 2: Dispatch workers in parallel
    worker_promises = []
    for task in tasks:
        promise = ctx.service_call(run_researcher, task)
        worker_promises.append(promise)

    await restate.gather(*worker_promises)
    findings = [await p for p in worker_promises]

    # Step 3: Combine results into a report
    report_result = await restate_writer.run(
        f"Topic: {req.topic}\n\nResearch findings:\n{json.dumps(findings)}",
    )

    return {"report": report_result.output, "task_count": len(tasks)}


researcher_service = restate.Service("Researcher")


@researcher_service.handler()
async def run_researcher(_ctx: restate.Context, task: ResearchTask) -> str:
    result = await restate_researcher.run(task.question)
    return result.output


# <end_here>


if __name__ == "__main__":
    import hypercorn
    import asyncio

    app = restate.app(services=[report_service, researcher_service])
    conf = hypercorn.Config()
    conf.bind = ["0.0.0.0:9080"]
    asyncio.run(hypercorn.asyncio.serve(app, conf))
