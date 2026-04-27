"""Multi-agent orchestration: an intake agent that routes to specialized
sub-agents.

LangChain's `create_agent` doesn't ship a first-class handoff primitive, but
the same pattern is expressed cleanly by exposing each specialist as a tool
on the intake agent. The intake agent picks which specialist to invoke;
each specialist call is a normal LangChain agent run, fully durable through
Restate's middleware.

Conversation history (and which specialist most recently handled a claim) is
stored in a Virtual Object so subsequent calls with the same key remember
prior context — analogous to OpenAI's `RestateSession`."""

import restate
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain_core.messages import AnyMessage, HumanMessage
from langchain_core.tools import tool

from restate.ext.langchain import RestateMiddleware, PydanticTypeAdapter

from utils.models import InsuranceClaim

MESSAGES_SERDE = PydanticTypeAdapter(list[AnyMessage])

MIDDLEWARE = [RestateMiddleware()]
MODEL = init_chat_model("openai:gpt-4o-mini")


# <start_here>
medical_agent = create_agent(
    model=MODEL,
    tools=[],
    system_prompt=(
        "You are a medical insurance specialist. Review medical claims for "
        "coverage and necessity. Approve/deny up to $50,000."
    ),
    middleware=MIDDLEWARE,
)

car_agent = create_agent(
    model=MODEL,
    tools=[],
    system_prompt=(
        "You are a car insurance specialist. Assess car claims for liability "
        "and damage. Approve/deny up to $25,000."
    ),
    middleware=MIDDLEWARE,
)


@tool
async def to_medical_specialist(claim_json: str) -> str:
    """Hand the claim to the medical specialist for evaluation."""
    result = await medical_agent.ainvoke(
        {"messages": [{"role": "user", "content": claim_json}]}
    )
    return result["messages"][-1].content


@tool
async def to_car_specialist(claim_json: str) -> str:
    """Hand the claim to the car specialist for evaluation."""
    result = await car_agent.ainvoke(
        {"messages": [{"role": "user", "content": claim_json}]}
    )
    return result["messages"][-1].content


intake_agent = create_agent(
    model=MODEL,
    tools=[to_medical_specialist, to_car_specialist],
    system_prompt=(
        "You are an intake agent. Route insurance claims to the appropriate "
        "specialist. Always call exactly one specialist tool, then summarize "
        "their decision."
    ),
    middleware=MIDDLEWARE,
)


agent_service = restate.VirtualObject("MultiAgentClaimApproval")


@agent_service.handler()
async def run(ctx: restate.ObjectContext, claim: InsuranceClaim) -> str:
    history = await ctx.get("messages", serde=MESSAGES_SERDE) or []
    history.append(HumanMessage(content=f"Claim: {claim.model_dump_json()}"))
    result = await intake_agent.ainvoke({"messages": history})
    ctx.set("messages", result["messages"], serde=MESSAGES_SERDE)
    return result["messages"][-1].content
# <end_here>


if __name__ == "__main__":
    import asyncio

    import hypercorn
    import hypercorn.asyncio

    app = restate.app(services=[agent_service])
    conf = hypercorn.Config()
    conf.bind = ["0.0.0.0:9080"]
    asyncio.run(hypercorn.asyncio.serve(app, conf))
