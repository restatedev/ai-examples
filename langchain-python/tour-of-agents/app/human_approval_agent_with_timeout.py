"""HITL with a timeout. Uses `restate.select` to race the awakeable against
a sleep, falling back to a default decision if the human doesn't reply in
time."""

from datetime import timedelta

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
    approval_id, approval_promise = restate_context().awakeable(type_hint=bool)

    await restate_context().run_typed(
        "Request review", request_human_review, claim=claim, awakeable_id=approval_id
    )

    # Wait at most 3 hours for a human reply.
    match await restate.select(
        approval=approval_promise,
        timeout=restate_context().sleep(timedelta(hours=3)),
    ):
        case ["approval", approved]:
            return "Approved" if approved else "Rejected"
        case _:
            return "Approval timed out - Evaluate with AI"


# <end_here>


agent = create_agent(
    model=init_chat_model("openai:gpt-5.4"),
    tools=[human_approval],
    system_prompt=(
        "You are an insurance claim evaluation agent. Use these rules:\n"
        "- if the amount is more than 1000, ask for human approval using tools;\n"
        "- if the amount is less than 1000, decide by yourself."
    ),
    middleware=[RestateMiddleware()],
)


agent_service = restate.Service("HumanClaimApprovalWithTimeoutsAgent")


@agent_service.handler()
async def run(_ctx: restate.Context, req: ClaimPrompt) -> str:
    result = await agent.ainvoke({"messages": req.message})
    return result["messages"][-1].content


if __name__ == "__main__":
    import asyncio

    import hypercorn
    import hypercorn.asyncio

    app = restate.app(services=[agent_service])
    conf = hypercorn.Config()
    conf.bind = ["0.0.0.0:9080"]
    asyncio.run(hypercorn.asyncio.serve(app, conf))
