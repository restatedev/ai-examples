"""
Orchestrator-Worker Pattern

Break down complex tasks into specialized subtasks and execute them in parallel.
If any worker fails, Restate retries only that worker while preserving other completed work.
"""

import json

import restate
from pydantic import BaseModel
from restate import RunOptions

from .util.litellm_call import llm_call


class ResearchTask(BaseModel):
    question: str


class ReportRequest(BaseModel):
    topic: str = "The impact of renewable energy on global economies"


# <start_here>
researcher_service = restate.Service("ResearchWorker")


@researcher_service.handler()
async def research(ctx: restate.Context, req: ResearchTask) -> dict:
    answer = await ctx.run_typed(
        "Research", llm_call,
        RunOptions(max_attempts=3),
        messages=req.question,
        system="You are a research assistant. Provide a concise, factual answer.",
    )
    return {"question": req.question, "answer": answer.content}


report_service = restate.Service("ResearchReport")


@report_service.handler()
async def generate(ctx: restate.Context, req: ReportRequest) -> dict:
    # Step 1: Orchestrator creates a research plan
    plan_result = await ctx.run_typed(
        "Create research plan", llm_call,
        RunOptions(max_attempts=3),
        messages=req.topic,
        system="""You are a research planner. Break the topic into 2-4 research
        sub-tasks. Respond with a JSON array of strings, each a specific
        research question. Example: ["question 1", "question 2"]""",
    )
    tasks = json.loads(plan_result.content)

    # Step 2: Dispatch workers in parallel
    worker_promises = []
    for task in tasks:
        promise = ctx.service_call(research, ResearchTask(question=task))
        worker_promises.append(promise)

    await restate.gather(*worker_promises)
    findings = [await p for p in worker_promises]

    # Step 3: Combine results into a report
    report = await ctx.run_typed(
        "Write report", llm_call,
        RunOptions(max_attempts=3),
        messages=f"Topic: {req.topic}\n\nResearch findings:\n{json.dumps(findings, indent=2)}",
        system="You are a report writer. Combine the research findings into a cohesive report.",
    )

    return {"report": report.content, "task_count": len(tasks)}
# <end_here>
