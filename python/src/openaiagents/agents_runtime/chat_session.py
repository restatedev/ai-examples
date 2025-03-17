from typing import TypedDict
from pydantic import BaseModel
import restate

from agents import (
    Agent,
    FunctionTool
)
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX
from agents.strict_schema import ensure_strict_json_schema

from restate_runner.restate_tool_router import restate_tool_router, EmbeddedRequest, EnrichedContext
from restate_runner.restate_agent_service import execute_agent_call, RunOpts, prettify_response
from src.openaiagents.agents_runtime.tool_invoice_sender import invoice_sender_svc, DelayedSendInvoiceRequest, \
    SendInvoiceRequest
from tool_faq import faq_agent_svc, LookupRequest

# TYPES

class CustomerChatRequest(BaseModel):
    customer_id: str
    user_input: str

class CustomerContext(TypedDict):
    """
    This is extra information about the customer that can be used to enrich the conversation
    or as parameters for invoking tools.

    The passenger_name is the full name of the passenger.
    The passenger_email is the email address of the passenger to send communication.
    The confirmation_number is the confirmation number of the flight.
    The seat_number is the seat number of the passenger.
    The flight_number is the flight number.
    """
    passenger_name: str | None
    passenger_email: str | None
    confirmation_number: str | None
    seat_number: str | None
    flight_number: str | None

# AGENTS

faq_agent = Agent[EnrichedContext[CustomerContext]](
    name=faq_agent_svc.name,
    handoff_description="A helpful agent that can answer questions about the airline.",
    instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
    You are an FAQ agent with name {faq_agent_svc.name}. 
    If you are speaking to a customer, you probably were transferred to from the triage agent.
    Use the following routine to support the customer.
    # Routine
    1. Identify the last question asked by the customer.
    2. Use the faq_lookup_tool to answer the question. Do not rely on your own knowledge.
    3. If you cannot answer the question, transfer back to the triage agent.
    """,
    tools=[FunctionTool(name="faq_lookup_tool",
                        description="A tool that can answer questions about the airline.",
                        on_invoke_tool=restate_tool_router,
                        params_json_schema=ensure_strict_json_schema(EmbeddedRequest[LookupRequest].model_json_schema()))],
)


invoice_sender = Agent[EnrichedContext[CustomerContext]](
    name=invoice_sender_svc.name,
    handoff_description="A helpful agent that can helps you with scheduling to receive an invoice after a specific delay.",
    instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
    You are an invoice sending scheduling agent, called {invoice_sender_svc.name}. 
    If you are speaking to a customer, you probably were transferred to from the triage agent.
    Use the following routine to support the customer.
    # Routine
    1. If the original message does not include the time or delay for the sending of the invoice, then assume the invoice should be send immediately with the send_invoice tool.
    If the original message does include a time or delay, then use the send_invoice_delayed tool. 
    If they give a date in the future, calculate the millisecond delay by subtracting the current date from the future date. 
    You can retrieve the name and the email of the customer from the context.
    2. If the customer asks a question that is not related to the routine, transfer back to the triage agent. """,
    tools=[FunctionTool(name="send_invoice",
                        description="Immediately sends an invoice",
                        on_invoke_tool=restate_tool_router,
                        params_json_schema=ensure_strict_json_schema(EmbeddedRequest[SendInvoiceRequest].model_json_schema())),
           FunctionTool(name="send_invoice_delayed",
                        description="Schedules the sending of an invoice after a delay specified in milliseconds.",
                        on_invoke_tool=restate_tool_router,
                        params_json_schema=ensure_strict_json_schema(EmbeddedRequest[DelayedSendInvoiceRequest].model_json_schema()))],
)


triage_agent = Agent[EnrichedContext[CustomerContext]](
    name="triage_agent",
    handoff_description="A triage agent that can delegate a customer's request to the appropriate agent.",
    instructions=(
        f"{RECOMMENDED_PROMPT_PREFIX} "
        "You are a helpful triaging agent. You can use your tools to delegate questions to other appropriate agents."
    ),
    handoffs=[
        faq_agent,
        invoice_sender,
    ],
)

faq_agent.handoffs.append(triage_agent)
invoice_sender.handoffs.append(triage_agent)

chat_agents = {
    triage_agent.name: triage_agent,
    faq_agent.name: faq_agent,
    invoice_sender.name: invoice_sender,
}

# CHAT SERVICE

chat_service = restate.VirtualObject("ChatService")

@chat_service.handler()
async def chat(ctx: restate.ObjectContext, req: CustomerChatRequest) -> str:

    # Retrieve the CustomerContext from an external CRM system
    customer_context = await ctx.run(
        "Get customer context",
        lambda: retrieve_customer_from_crm(req.customer_id))

    result = await execute_agent_call(ctx, RunOpts(
        agents=chat_agents,
        init_agent=triage_agent,
        input=req.user_input, # this is the input for the LLM call
        custom_context=customer_context # this does not get passed in the LLM call, only as input to tools
    ))

    return prettify_response(result)


app = restate.app(services=[chat_service, faq_agent_svc, invoice_sender_svc])



# -------------- Stubs ----------------

def retrieve_customer_from_crm(customer_id):
    return CustomerContext(passenger_name="Alice",
                           passenger_email="alice@gmail.com",
                           confirmation_number="123456",
                           seat_number="12A",
                           flight_number="FLT-123")