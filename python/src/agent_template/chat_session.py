
import restate
from pydantic import BaseModel
from typing import Any

from restate_runner.agent_restate import run, Agent, RestateTool, RECOMMENDED_PROMPT_PREFIX
from services import faq_service, booking_object

# AGENTS
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
        RestateTool(tool_call=faq_service.faq_lookup_tool)
    ],
)

booking_info_agent = Agent(
    name="Booking Info Agent",
    handoff_description="A helpful agent that can answer questions about the customer's booking: confirmation number, flight number, passenger name, passenger email, and seat number.",
    instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
    You are a booking info agent that knows everything about a customer's booking
    If you are speaking to a customer, you probably were transferred to from the triage agent.
    Use the following routine to support the customer.
    # Routine
    1. Identify the last question asked by the customer. Make sure you know the booking ID the customer is asking about.
    If the customer did not provide a booking ID, ask for it. Never come up with the booking ID yourself.
    2. Use the get_info tool to get extra information to answer the question. 
    3. If you cannot answer the question, transfer back to the triage agent.
    """,
    tools=[RestateTool(tool_call=booking_object.get_info)],
)

send_invoice_agent = Agent(
    name="Send Invoice Agent",
    handoff_description="A helpful agent that can helps you with scheduling to receive an invoice after a specific delay.",
    instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
    You are an agent that helps with answering questions and queries on flight bookings. 
    If you are speaking to a customer, you probably were transferred to from the triage agent.
    Use the following routine to support the customer.
    # Routine
    1. Make sure you know the booking ID the customer is asking about.
    If the customer did not provide a booking ID, ask for it. Never come up with the booking ID yourself.
    2. If the original message does not include the time or delay for the sending of the invoice, then assume the invoice should be send immediately with the send_invoice tool.
    If the original message does include a time or delay, then use the send_invoice_delayed tool. 
    If they give a date in the future, calculate the millisecond delay by subtracting the current date from the future date. 
    3. If the customer asks a question that is not related to the routine, transfer back to the triage agent.""",
    tools=[RestateTool(tool_call=booking_object.send_invoice)],
)

update_seat_agent = Agent(
    name="Update Seat Agent",
    handoff_description="A helpful agent that can helps you with scheduling to receive an invoice after a specific delay.",
    instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
    You are an agent that helps with answering questions and queries on flight bookings. 
    If you are speaking to a customer, you probably were transferred to from the triage agent.
    Use the following routine to support the customer.
    # Routine
    1. Make sure you know the booking ID the customer is asking about.
    If the customer did not provide a booking ID, ask for it. Never come up with the booking ID yourself.
    2. If the customer asks for a seat change, you can use the update_seat tool to update the seat on the flight.
    Ask the customer what their desired seat number is.
    Use the update seat tool to update the seat on the flight.
    3. If the customer asks a question that is not related to the routine, transfer back to the triage agent.""",
    tools=[RestateTool(tool_call=booking_object.update_seat)],
)


triage_agent = Agent(
    name="Triage Agent",
    handoff_description="A triage agent that can delegate a customer's request to the appropriate agent.",
    instructions= (f"{RECOMMENDED_PROMPT_PREFIX}"
                   "You are a helpful triaging agent. You can use your tools to delegate questions to other appropriate agents."
                   ),
    handoffs=[faq_agent.name, booking_info_agent.name, send_invoice_agent.name, update_seat_agent.name],
)

faq_agent.handoffs.append(triage_agent.name)
booking_info_agent.handoffs.append(triage_agent.name)
send_invoice_agent.handoffs.append(triage_agent.name)
update_seat_agent.handoffs.append(triage_agent.name)


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
        agents=[triage_agent, faq_agent, booking_info_agent, send_invoice_agent, update_seat_agent],
        message=req.user_input, # this is the input for the LLM call
    )

    return result.messages

