import json
import typing
from typing import Generic, TypeVar

import restate
from agents import (
    Agent,
    RunContextWrapper,
    TContext
)
from agents.tool import function_tool
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX
from pydantic import BaseModel

class EnrichedContext(typing.TypedDict):
    context: TContext | None
    restate_context: restate.ObjectContext

class LookupRequest(BaseModel):
    """
    A request to the faq_lookup_tool.
    The question is the question to ask.
    """
    question: str


P = typing.TypeVar("P")


class EmbeddedLookupRequest(BaseModel):
    """
    A request to the faq_lookup_tool.
    The tool_name is the name of the tool to call: faq_lookup_tool
    The request is the request to the tool.
    """
    tool_name: str
    request: LookupRequest

async def restate_tool_router(context: RunContextWrapper[EnrichedContext], req: EmbeddedLookupRequest) -> str:
    agent_name = req.tool_name.split("_")[0] + "_agent"
    print(f"will call {agent_name} with {req.tool_name} and {req.request}")
    try:
        tool_response = await context.context["restate_context"].generic_call(service=agent_name, handler=req.tool_name, arg=json.dumps(req.request.model_dump()).encode("utf-8"))
        response = tool_response.decode("utf-8")
        print(f"response: {response}")
        return response
    except Exception as e:
        print(f"error: {e}")
        return e.add_note("The tool was not able to be called. Make sure the tool_name is correct and the request is valid.")

faq_agent = Agent[EnrichedContext](
    name="faq_agent",
    handoff_description="A helpful agent that can answer questions about the airline.",
    instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
    You are an FAQ agent. If you are speaking to a customer, you probably were transferred to from the triage agent.
    Use the following routine to support the customer.
    # Routine
    1. Identify the last question asked by the customer.
    2. Use the faq_lookup_tool to answer the question. Do not rely on your own knowledge.
    3. If you cannot answer the question, transfer back to the triage agent.
    """,
    tools=[function_tool(func=restate_tool_router, name_override="faq_lookup_tool", description_override="A tool that can answer questions about the airline.")],
)

triage_agent = Agent[EnrichedContext](
    name="triage_agent",
    handoff_description="A triage agent that can delegate a customer's request to the appropriate agent.",
    instructions=(
        f"{RECOMMENDED_PROMPT_PREFIX} "
        "You are a helpful triaging agent. You can use your tools to delegate questions to other appropriate agents."
    ),
    handoffs=[
        faq_agent,
    ],
)

faq_agent.handoffs.append(triage_agent)

AGENTS = {
    triage_agent.name: triage_agent,
    faq_agent.name: faq_agent,
}