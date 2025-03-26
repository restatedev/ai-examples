
import restate
from pydantic import BaseModel
from typing import Any

from restate_runner.agent_restate import run, Agent, Tool, RECOMMENDED_PROMPT_PREFIX

# AGENTS

faq_service = restate.Service("FaqAgent")


class LookupRequest(BaseModel):
    """
    A request to the faq_lookup_tool.
    This request is the input for the tool with name: faq_lookup_tool
    The question parameter is the question that the tool will answer.
    """
    question: str


@faq_service.handler()
async def faq_lookup_tool(ctx: restate.Context, req: LookupRequest) -> str:
    question = req.question
    if "bag" in question or "baggage" in question:
        return (
            "You are allowed to bring one bag on the plane. "
            "It must be under 50 pounds and 22 inches x 14 inches x 9 inches."
        )
    elif "seats" in question or "plane" in question:
        return (
            "There are 120 seats on the plane. "
            "There are 22 business class seats and 98 economy seats. "
            "Exit rows are rows 4 and 16. "
            "Rows 5-8 are Economy Plus, with extra legroom. "
        )
    elif "wifi" in question:
        return "We have free wifi on the plane, join Airline-Wifi"
    return "I'm sorry, I don't know the answer to that question."

# There are two ways to integrate Restate handlers as tools for your agents
# 1. By using the restate_tool_router function to route the call to the appropriate handler (see faq_agent below)
#    Pro: You don't need to write the glue function for each tool
#    Con: You cannot impact or adapt the specifics of how the handler is called (use custom context to enrich the arguments, specify delay, etc.)
# 2. By specifying a tool which calls the Restate handler (see send_invoice_tool below)
#    Pro: You can adapt the arguments, specify delay, etc.
#    Con: You need to write a glue function for each tool

faq_agent = Agent(
    name="FAQ Agent",
    handoff_description="A helpful agent that can answer questions about the airline.",
    instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
    You are an FAQ agent. 
    If you are speaking to a customer, you probably were transferred to from the triage agent.
    Use the following routine to support the customer.
    # Routine
    1. Identify the last question asked by the customer.
    2. Use the faq_lookup_tool to answer the question. Do not rely on your own knowledge.
    3. If you cannot answer the question with any of the tools, then transfer back to the triage agent.
    """,
    tools=[
        Tool(name="faq_lookup_tool",
             handler=faq_lookup_tool,
             description="A tool that can answer questions about the airline.",
             input_type=LookupRequest)
    ],
    handoffs=[]
)

triage_agent = Agent(
    name="Triage Agent",
    handoff_description="A triage agent that can delegate a customer's request to the appropriate agent.",
    instructions= (f"{RECOMMENDED_PROMPT_PREFIX}"
                   "You are a helpful triaging agent. You can use your tools to delegate questions to other appropriate agents."
                   ),
    tools=[],
    handoffs=[faq_agent.name],
)

faq_agent.handoffs.append(triage_agent.name)

# CHAT SERVICE
chat_service = restate.VirtualObject("ChatService")


class CustomerChatRequest(BaseModel):
    booking_id: str | None
    user_input: str


@chat_service.handler()
async def chat(ctx: restate.ObjectContext, req: CustomerChatRequest) -> list[dict[str, Any]]:
    print("chat handler called")
    result = await run(
        ctx=ctx,
        starting_agent=triage_agent,
        agents=[triage_agent, faq_agent],
        message=req.user_input, # this is the input for the LLM call
    )

    return result.messages

