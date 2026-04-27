"""Human-in-the-loop via a Restate awakeable.

The agent calls `human_approval` for high-value claims. The tool creates an
awakeable, sends its id to a (simulated) human reviewer, and suspends the
invocation until someone resolves the awakeable via the Restate API."""

import restate
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain_core.tools import tool

from restate.ext.langchain import RestateMiddleware, restate_context

from utils.models import ClaimPrompt, InsuranceClaim
from utils.utils import request_human_review


# <start_here>
@tool
async def human_approval(claim: InsuranceClaim) -> str:
    """Ask for human approval for high-value claims."""
    ctx = restate_context()

    # Create an awakeable that a human can resolve via the Restate API.
    approval_id, approval_promise = ctx.awakeable(type_hint=str)

    # Notify the reviewer (durable step).
    await ctx.run_typed(
        "Request review", request_human_review, claim=claim, awakeable_id=approval_id
    )

    # Suspend until resolved.
    return await approval_promise


# <end_here>


agent = create_agent(
    model=init_chat_model("openai:gpt-4o-mini"),
    tools=[human_approval],
    system_prompt=(
        "You are an insurance claim evaluation agent. Use these rules:\n"
        "- if the amount is more than 1000, ask for human approval using tools;\n"
        "- if the amount is less than 1000, decide by yourself."
    ),
    middleware=[RestateMiddleware()],
)


agent_service = restate.Service("HumanClaimApprovalAgent")


@agent_service.handler()
async def run(_ctx: restate.Context, req: ClaimPrompt) -> str:
    result = await agent.ainvoke({"messages": [{"role": "user", "content": req.message}]})
    return result["messages"][-1].content


if __name__ == "__main__":
    import asyncio

    import hypercorn
    import hypercorn.asyncio

    app = restate.app(services=[agent_service])
    conf = hypercorn.Config()
    conf.bind = ["0.0.0.0:9080"]
    asyncio.run(hypercorn.asyncio.serve(app, conf))
