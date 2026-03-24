import restate

from pydantic_ai import Agent, RunContext
from restate.ext.pydantic import RestateAgent, restate_context

from utils.models import ClaimPrompt, InsuranceClaim
from utils.utils import request_human_review

agent = Agent(
    "openai:gpt-4o-mini",
    system_prompt="""You are an insurance claim evaluation agent. Use these rules:
    - if the amount is more than 1000, ask for human approval using tools;
    - if the amount is less than 1000, decide by yourself.""",
)


# <start_here>
@agent.tool
async def human_approval(_run_ctx: RunContext[None], claim: InsuranceClaim) -> str:
    """Ask for human approval for high-value claims."""

    # Create an awakeable for human approval
    approval_id, approval_promise = restate_context().awakeable(type_hint=str)

    # Request human review
    await restate_context().run_typed(
        "Request review", request_human_review, claim=claim, awakeable_id=approval_id
    )

    # Wait for human approval
    return await approval_promise


# <end_here>

restate_agent = RestateAgent(agent)
agent_service = restate.Service("HumanClaimApprovalAgent")


@agent_service.handler()
async def run(_ctx: restate.Context, req: ClaimPrompt) -> str:
    result = await restate_agent.run(req.message)
    return result.output


if __name__ == "__main__":
    import hypercorn
    import asyncio

    app = restate.app(services=[agent_service])
    conf = hypercorn.Config()
    conf.bind = ["0.0.0.0:9080"]
    asyncio.run(hypercorn.asyncio.serve(app, conf))
