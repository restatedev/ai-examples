"""LLM-as-a-Judge evaluation workflow.

Runs as an async Restate service — the claim agent fires it off via a one-way
send so evaluation never blocks the main request.  Restate guarantees the
evaluation runs to completion (with retries on failure) without extra infra.

Flow:
  1. Receive the original trace_id, claim input, and agent output
  2. Ask an LLM judge to score the agent's work (durable LLM call)
  3. Write the score back to LangFuse on the original claim trace
"""

import restate

from agents import Agent
from langfuse import get_client
from restate.ext.openai import DurableRunner

from utils.utils import EvaluationScore, EvaluationRequest

# <start_here>

langfuse = get_client()

judge_agent = Agent(
    name="ClaimEvaluationJudge",
    instructions=(
        "You are an expert evaluator of insurance claim processing. "
        "Rate the overall quality of the claim agent's response as a score "
        "between 0.0 and 1.0, and provide a brief reason for your rating."
    ),
    output_type=EvaluationScore,
)

evaluation_service = restate.Service("LLMJudgeEvaluation")


@evaluation_service.handler()
async def evaluate(ctx: restate.Context, req: EvaluationRequest) -> None:
    # Step 1: Run the LLM judge (durable — retried on failure)
    result = await DurableRunner.run(
        judge_agent,
        f"Evaluate this insurance claim processing:\n\n"
        f"**Claim Input:**\n{req.input}\n\n"
        f"**Agent Output:**\n{req.output}",
    )
    evaluation: EvaluationScore = result.final_output

    # Step 2: Write the score to LangFuse on the original claim trace
    async def score_trace() -> None:
        langfuse.create_score(
            trace_id=req.trace_id(),
            name="quality",
            value=evaluation.score,
            data_type="NUMERIC",
            comment=evaluation.reason,
        )
        langfuse.flush()

    await ctx.run_typed("Score trace in Langfuse", score_trace)


# <end_here>
