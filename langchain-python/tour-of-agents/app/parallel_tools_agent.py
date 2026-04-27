"""Parallel sub-steps inside a single tool, fan-out via `restate.gather`.

The middleware turnstile guarantees that this tool body runs sequentially
with respect to *other* tool calls in the same LLM turn. Inside one tool
body we are free to fan out — each `ctx.run_typed` is its own durable
journal entry."""

import restate
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain_core.tools import tool

from restate.ext.langchain import RestateMiddleware, restate_context

from utils.models import InsuranceClaim
from utils.utils import check_eligibility, check_fraud, compare_to_standard_rates


# <start_here>
@tool
async def calculate_metrics(claim: InsuranceClaim) -> list[str]:
    """Calculate claim metrics: eligibility, cost, and fraud risk."""
    ctx = restate_context()

    # Run the sub-steps in parallel with durable execution.
    eligibility, cost, fraud = await restate.gather(
        ctx.run_typed("eligibility", check_eligibility, claim=claim),
        ctx.run_typed("cost", compare_to_standard_rates, claim=claim),
        ctx.run_typed("fraud", check_fraud, claim=claim),
    )
    return [await eligibility, await cost, await fraud]


# <end_here>


agent = create_agent(
    model=init_chat_model("openai:gpt-5.4"),
    tools=[calculate_metrics],
    system_prompt=(
        "You are a claim analysis agent. Use the calculate_metrics tool and "
        "decide whether to approve."
    ),
    middleware=[RestateMiddleware()],
)


agent_service = restate.Service("ParallelToolClaimAgent")


@agent_service.handler()
async def run(_ctx: restate.Context, claim: InsuranceClaim) -> str:
    result = await agent.ainvoke(
        {"messages": [{"role": "user", "content": f"Claim: {claim.model_dump_json()}"}]}
    )
    return result["messages"][-1].content


if __name__ == "__main__":
    import asyncio

    import hypercorn
    import hypercorn.asyncio

    app = restate.app(services=[agent_service])
    conf = hypercorn.Config()
    conf.bind = ["0.0.0.0:9080"]
    asyncio.run(hypercorn.asyncio.serve(app, conf))
