"""Orchestrator-worker pattern: a planner agent breaks a topic into research
tasks, parallel researcher services execute them, and a writer agent
combines the findings into a final report."""

import json
import restate

from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from restate.ext.langchain import RestateMiddleware

from utils.models import ReportRequest, ResearchTask, TaskList

# <start_here>
planner = create_agent(
    model=init_chat_model("openai:gpt-5.4"),
    system_prompt="You are a research planner. Break the topic into 2-4 research sub-tasks.",
    response_format=TaskList,
    middleware=[RestateMiddleware()],
)

researcher = create_agent(
    model=init_chat_model("openai:gpt-5.4"),
    system_prompt="You are a research assistant. Provide a concise, factual answer.",
    middleware=[RestateMiddleware()],
)

writer = create_agent(
    model=init_chat_model("openai:gpt-5.4"),
    system_prompt="You are a report writer. Combine the research findings into a cohesive report.",
    middleware=[RestateMiddleware()],
)

report_service = restate.Service("ResearchReport")


@report_service.handler()
async def generate(ctx: restate.Context, req: ReportRequest) -> dict:
    # Step 1: Orchestrator creates a research plan.
    plan_result = await planner.ainvoke({"messages": req.topic})
    tasks: list[ResearchTask] = plan_result["structured_response"].tasks

    # Step 2: Dispatch researchers in parallel.
    worker_promises = [ctx.service_call(run_researcher, task) for task in tasks]
    await restate.gather(*worker_promises)
    findings = [await p for p in worker_promises]

    # Step 3: Combine into a report.
    message = f"Topic: {req.topic}\n\nResearch findings:\n{json.dumps(findings)}"
    report_result = await writer.ainvoke({"messages": message})

    return {"report": report_result["messages"][-1].content, "task_count": len(tasks)}


researcher_service = restate.Service("Researcher")


@researcher_service.handler()
async def run_researcher(_ctx: restate.Context, task: ResearchTask) -> str:
    result = await researcher.ainvoke({"messages": task.question})
    return result["messages"][-1].content


# <end_here>


if __name__ == "__main__":
    import asyncio

    import hypercorn
    import hypercorn.asyncio

    app = restate.app(services=[report_service, researcher_service])
    conf = hypercorn.Config()
    conf.bind = ["0.0.0.0:9080"]
    asyncio.run(hypercorn.asyncio.serve(app, conf))
