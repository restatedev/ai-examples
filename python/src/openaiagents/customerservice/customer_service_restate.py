from __future__ import annotations as _annotations

from datetime import timedelta

import restate
from pydantic import BaseModel
from restate.serde import PydanticJsonSerde

from agents import (
    Agent,
    HandoffOutputItem,
    ItemHelpers,
    MessageOutputItem,
    RunContextWrapper,
    RunResult,
    ToolCallItem,
    ToolCallOutputItem,
    function_tool,
    handoff,
)
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX

from src.openaiagents.customerservice.restate_agent_runner import RestateRunner


### CONTEXT

class CustomerChatRequest(BaseModel):
    customer_id: str
    user_input: str

class CustomerContext(BaseModel):
    passenger_name: str | None = None
    confirmation_number: str | None = None
    seat_number: str | None = None
    flight_number: str | None = None

### TOOLS

@function_tool(
    name_override="faq_lookup_tool", description_override="Lookup frequently asked questions."
)
async def faq_lookup_tool(question: str) -> str:
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



@function_tool
async def update_seat(
    context: RunContextWrapper[restate.ObjectContext], confirmation_number: str, new_seat: str
) -> str:
    """
    Update the seat for a given confirmation number.

    Args:
        confirmation_number: The confirmation number for the flight.
        new_seat: The new seat to update to.
    """
    # Update the context based on the customer's input
    customer_context = await context.context.get("customer_context", PydanticJsonSerde(CustomerContext))
    if customer_context is None:
        return f"Could not find customer context for confirmation number {confirmation_number}"
    customer_context.seat_number = new_seat
    context.context.set("customer_context", customer_context, PydanticJsonSerde(CustomerContext))


    # Ensure that the flight number has been set by the incoming handoff
    assert customer_context.flight_number is not None, "Flight number is required"
    return f"Updated seat to {new_seat} for confirmation number {confirmation_number} and flight number {customer_context.flight_number}"


### HOOKS

async def on_seat_booking_handoff(context: RunContextWrapper[restate.ObjectContext]) -> None:
    # Do something on the handoff
    pass


### AGENTS

faq_agent = Agent[restate.ObjectContext](
    name="FAQ Agent",
    handoff_description="A helpful agent that can answer questions about the airline.",
    instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
    You are an FAQ agent. If you are speaking to a customer, you probably were transferred to from the triage agent.
    Use the following routine to support the customer.
    # Routine
    1. Identify the last question asked by the customer.
    2. Use the faq lookup tool to answer the question. Do not rely on your own knowledge.
    3. If you cannot answer the question, transfer back to the triage agent.""",
    tools=[faq_lookup_tool],
)

seat_booking_agent = Agent[restate.ObjectContext](
    name="Seat Booking Agent",
    handoff_description="A helpful agent that can update a seat on a flight.",
    instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
    You are a seat booking agent. If you are speaking to a customer, you probably were transferred to from the triage agent.
    Use the following routine to support the customer.
    # Routine
    1. Ask for their confirmation number.
    2. Ask the customer what their desired seat number is.
    3. Use the update seat tool to update the seat on the flight.
    If the customer asks a question that is not related to the routine, transfer back to the triage agent. """,
    tools=[update_seat],
)

triage_agent = Agent[restate.ObjectContext](
    name="Triage Agent",
    handoff_description="A triage agent that can delegate a customer's request to the appropriate agent.",
    instructions=(
        f"{RECOMMENDED_PROMPT_PREFIX} "
        "You are a helpful triaging agent. You can use your tools to delegate questions to other appropriate agents."
    ),
    handoffs=[
        faq_agent,
        handoff(agent=seat_booking_agent, on_handoff=on_seat_booking_handoff),
    ],
)

faq_agent.handoffs.append(triage_agent)
seat_booking_agent.handoffs.append(triage_agent)

AGENTS = {
    triage_agent.name: triage_agent,
    faq_agent.name: faq_agent,
    seat_booking_agent.name: seat_booking_agent,
}

### RUN
customer_service_session = restate.VirtualObject("CustomerServiceSession")

@customer_service_session.handler()
async def chat(ctx: restate.ObjectContext, req: CustomerChatRequest) -> None:

    # Retrieve the current agent of this session
    current_agent_name = await ctx.get("current_agent_name")
    if current_agent_name is None:
        current_agent_name = triage_agent.name
        ctx.set("current_agent_name", current_agent_name)
    current_agent: Agent[restate.ObjectContext] = AGENTS[current_agent_name]

    # If this is the first time, then retrieve the CustomerContext from an external CRM system
    if await ctx.get("customer_context") is None:
        customer_context = await ctx.run(
            "Get customer context",
            lambda: retrieve_customer_from_crm(req.customer_id),
            PydanticJsonSerde(CustomerContext))
        ctx.set("customer_context", customer_context, PydanticJsonSerde(CustomerContext))

    # Run the input through the agent
    input_items = await ctx.get("input_items") or []
    input_items.append({"content": req.user_input, "role": "user"})
    result: RunResult = await RestateRunner.run(
        current_agent,
        input_items,
        max_turns=10,
        context=ctx)
    input_items = result.to_input_list()
    ctx.set("input_items", input_items)
    ctx.set("current_agent_name", result.last_agent.name)

    return prettify_response(result)


app = restate.app(services=[customer_service_session])











# -----------------------------------------------------------------------------------------------------------------------------
# --------------------------------------------------HELPERS/STUBS--------------------------------------------------------------


def retrieve_customer_from_crm(customer_id):
    return CustomerContext(passenger_name="Alice", confirmation_number="123456", seat_number="12A", flight_number="FLT-123")

def prettify_response(result: RunResult):
    response = ""
    for new_item in result.new_items:
        agent_name = new_item.agent.name
        if isinstance(new_item, MessageOutputItem):
            print(f"{agent_name}: {ItemHelpers.text_message_output(new_item)}")
            response += f"{agent_name}: {ItemHelpers.text_message_output(new_item)}\n"
        elif isinstance(new_item, HandoffOutputItem):
            print(
                f"Handed off from {new_item.source_agent.name} to {new_item.target_agent.name}"
            )
            response += f"Handed off from {new_item.source_agent.name} to {new_item.target_agent.name}\n"
        elif isinstance(new_item, ToolCallItem):
            print(f"{agent_name}: Calling a tool")
            response += f"{agent_name}: Calling a tool\n"
        elif isinstance(new_item, ToolCallOutputItem):
            print(f"{agent_name}: Tool call output: {new_item.output}")
            response += f"{agent_name}: Tool call output: {new_item.output}"
        else:
            print(f"{agent_name}: Skipping item: {new_item.__class__.__name__}")
            response += f"{agent_name}: Skipping item: {new_item.__class__.__name__}\n"
    return response
