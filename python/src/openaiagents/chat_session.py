import restate

from datetime import timedelta
from pydantic import BaseModel
from agents import (
    Agent,
    FunctionTool,
    function_tool,
    handoff,
    RunContextWrapper,
)
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX
from agents.strict_schema import ensure_strict_json_schema

from restate_runner.restate_tool_router import restate_tool_router, EmbeddedRequest, EnrichedContext
from restate_runner.restate_agent_service import execute_agent_call, RunOpts, prettify_response

from src.openaiagents.services import booking_object
from src.openaiagents.services.booking_object import Booking
from src.openaiagents.services.faq_service import faq_service, LookupRequest

# TOOLS

@function_tool()
async def send_invoice_tool(
        context: RunContextWrapper[EnrichedContext[Booking]], delay_millis: int
) -> str:
    """
    Schedules the sending of an invoice after a delay specified in milliseconds.

    Args:
        delay_millis: The delay in milliseconds to send the invoice. If 0, the invoice is sent immediately.
    """
    booking: Booking = context.context["custom_context"]
    restate_context = context.context["restate_context"]
    if delay_millis == 0:
        return await restate_context.object_call(booking_object.send_invoice,
                                                 key=booking.confirmation_number,
                                                 arg=None)
    else:
        restate_context.object_send(booking_object.send_invoice,
                                    key=booking.confirmation_number,
                                    arg=None,
                                    send_delay=timedelta(milliseconds=delay_millis))
        return f"Scheduled invoice sending for booking {booking.confirmation_number}"


@function_tool()
async def update_seat_tool(context: RunContextWrapper[EnrichedContext[Booking]], new_seat_number: str) -> str:
    """
    Update the seat for a given customer

    Args:
        new_seat_number: The new seat to update to.
    """
    booking: Booking = context.context["custom_context"]
    restate_context = context.context["restate_context"]
    # Update the context based on the customer's input
    return await restate_context.object_call(booking_object.update_seat,
                                             key=booking.confirmation_number,
                                             arg=new_seat_number)


@function_tool()
async def booking_info_tool(context: RunContextWrapper[EnrichedContext[Booking]]) -> str:
    """
    Get the booking information: confirmation number, flight number, passenger name, passenger email, and seat number.
    """
    print(context.context["custom_context"])
    return f"Here is your booking info {context.context["custom_context"].model_dump_json()}"


# HOOKS

async def on_seat_booking_handoff(context: RunContextWrapper[EnrichedContext[Booking]]) -> None:
    # Do something on the handoff
    pass



# AGENTS

# There are two ways to integrate Restate handlers as tools for your agents
# 1. By using the restate_tool_router function to route the call to the appropriate handler (see faq_agent below)
#    Pro: You don't need to write the glue function for each tool
#    Con: You cannot impact or adapt the specifics of how the handler is called (use custom context to enrich the arguments, specify delay, etc.)
# 2. By specifying a tool which calls the Restate handler (see send_invoice_tool below)
#    Pro: You can adapt the arguments, specify delay, etc.
#    Con: You need to write a glue function for each tool

faq_agent = Agent[EnrichedContext[Booking]](
    name=faq_service.name,
    handoff_description="A helpful agent that can answer questions about the airline.",
    instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
    You are an FAQ agent with name {faq_service.name}. 
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

booking_info_agent = Agent[EnrichedContext[Booking]](
    name="Booking Info Agent",
    handoff_description="A helpful agent that can answer questions about the customer's booking: confirmation number, flight number, passenger name, passenger email, and seat number.",
    instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
    You are a booking info agent that knows everything about a customer's booking
    If you are speaking to a customer, you probably were transferred to from the triage agent.
    Use the following routine to support the customer.
    # Routine
    1. Identify the last question asked by the customer.
    2. Use the get_booking_info tool to get extra information to answer the question. 
    3. If you cannot answer the question, transfer back to the triage agent.
    """,
    tools=[booking_info_tool],
)

send_invoice_agent = Agent[EnrichedContext[Booking]](
    name="Send Invoice Agent",
    handoff_description="A helpful agent that can helps you with scheduling to receive an invoice after a specific delay.",
    instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
    You are an agent that helps with answering questions and queries on flight bookings. 
    If you are speaking to a customer, you probably were transferred to from the triage agent.
    Use the following routine to support the customer.
    # Routine
    1. If the original message does not include the time or delay for the sending of the invoice, then assume the invoice should be send immediately with the send_invoice tool.
    If the original message does include a time or delay, then use the send_invoice_delayed tool. 
    If they give a date in the future, calculate the millisecond delay by subtracting the current date from the future date. 
    2. If the customer asks a question that is not related to the routine, transfer back to the triage agent.""",
    tools=[send_invoice_tool],
)

update_seat_agent = Agent[EnrichedContext[Booking]](
    name="Update Seat Agent",
    handoff_description="A helpful agent that can helps you with scheduling to receive an invoice after a specific delay.",
    instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
    You are an agent that helps with answering questions and queries on flight bookings. 
    If you are speaking to a customer, you probably were transferred to from the triage agent.
    Use the following routine to support the customer.
    # Routine
    1. If the customer asks for a seat change, you can use the update_seat tool to update the seat on the flight.
    Ask the customer what their desired seat number is.
    Use the update seat tool to update the seat on the flight.
    2. If the customer asks a question that is not related to the routine, transfer back to the triage agent.""",
    tools=[update_seat_tool],
)

triage_agent = Agent[EnrichedContext[Booking]](
    name="Triage Agent",
    handoff_description="A triage agent that can delegate a customer's request to the appropriate agent.",
    instructions=(
        f"{RECOMMENDED_PROMPT_PREFIX} "
        "You are a helpful triaging agent. You can use your tools to delegate questions to other appropriate agents."
    ),
    handoffs=[
        faq_agent,
        booking_info_agent,
        send_invoice_agent,
        handoff(agent=update_seat_agent, on_handoff=on_seat_booking_handoff),
    ],
)

faq_agent.handoffs.append(triage_agent)
booking_info_agent.handoffs.append(triage_agent)
send_invoice_agent.handoffs.append(triage_agent)
update_seat_agent.handoffs.append(triage_agent)

chat_agents = {
    triage_agent.name: triage_agent,
    faq_agent.name: faq_agent,
    booking_info_agent.name: booking_info_agent,
    send_invoice_agent.name: send_invoice_agent,
    update_seat_agent.name: update_seat_agent,
}

# CHAT SERVICE

chat_service = restate.VirtualObject("ChatService")


class CustomerChatRequest(BaseModel):
    booking_id: str | None
    user_input: str


@chat_service.handler()
async def chat(ctx: restate.ObjectContext, req: CustomerChatRequest) -> str:
    """
    A chat service that lets a customer interact with their bookings.
    The customer can ask questions, request invoices, and update their seat.

    Args:
    :param ctx: The Restate context that tracks the state of the conversation.
    :param req: The request to the chat service.
    :return: The response from the chat service.
    """

    if req.booking_id is not None:
        booking = await ctx.object_call(booking_object.get_info, key=req.booking_id, arg=None)
    else:
        booking = None

    print(booking)
    result = await execute_agent_call(ctx, RunOpts(
        agents=chat_agents,
        init_agent=triage_agent,
        input=req.user_input, # this is the input for the LLM call
        custom_context=booking # this does not get passed in the LLM call, only as input to tools
    ))

    return prettify_response(result)
