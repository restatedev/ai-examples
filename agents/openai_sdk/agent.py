import agents
import restate
from openai.types.responses.response_input_param import Message

from pydantic import BaseModel, Field
from agents import (
    Agent,
    function_tool,
    handoff,
    RunContextWrapper,
)
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX

from datetime import datetime


class AirlineAgentContext(BaseModel):
    passenger_name: str | None = None
    confirmation_number: str | None = None
    seat_number: str | None = None
    flight_number: str | None = None


# TOOLS


@function_tool(
    name_override="faq_lookup_tool",
    description_override="Lookup frequently asked questions.",
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
    context: RunContextWrapper[AirlineAgentContext],
    confirmation_number: str,
    new_seat: str,
) -> str:
    """
    Update the seat for a given confirmation number.

    Args:
        confirmation_number: The confirmation number for the flight.
        new_seat: The new seat to update to.
    """
    # Update the context based on the customer's input
    context.context.confirmation_number = confirmation_number
    context.context.seat_number = new_seat
    return f"Updated seat to {new_seat} for confirmation number {confirmation_number}"


def request_customer_info():
    return AirlineAgentContext(passenger_name="John Doe", confirmation_number="12345", seat_number="12A", flight_number="AA123")


### AGENTS

faq_agent = Agent[AirlineAgentContext](
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

seat_booking_agent = Agent[AirlineAgentContext](
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

triage_agent = Agent[AirlineAgentContext](
    name="Triage Agent",
    handoff_description="A triage agent that can delegate a customer's request to the appropriate agent.",
    instructions=(
        f"{RECOMMENDED_PROMPT_PREFIX} "
        "You are a helpful triaging agent. You can use your tools to delegate questions to other appropriate agents."
    ),
    handoffs=[
        faq_agent,
        handoff(agent=seat_booking_agent),
    ],
)

faq_agent.handoffs.append(triage_agent)
seat_booking_agent.handoffs.append(triage_agent)

agent_dict = {agent.name: agent for agent in [faq_agent, seat_booking_agent, triage_agent]}

# AGENT

# Keyed by conversation id
agent = restate.VirtualObject("Agent")

# Keys of the K/V state stored in Restate per chat
INPUT_ITEMS = "input-items"



@agent.handler()
async def run(ctx: restate.ObjectContext, req: str) -> str:
    """
    Send a message to the agent.

    Args:
        req (str): The message to send to the agent.

    Returns:
        str: The response from the agent.
    """

    input_items = await ctx.get(INPUT_ITEMS) or []
    input_items.append({ "role": "user", "content": req })
    ctx.set(INPUT_ITEMS, input_items)

    last_agent_name = await ctx.get("agent") or triage_agent.name
    last_agent = agent_dict[last_agent_name]

    agent_context = await ctx.run("request customer info", lambda: request_customer_info(), type_hint=AirlineAgentContext)

    async def run_agent_session() -> tuple[str, str]:
        result = await agents.Runner.run(last_agent, input=input_items, context=agent_context)
        return str(result.final_output), result.last_agent.name

    output, last_agent_name = await ctx.run("run agent session", run_agent_session)
    ctx.set("agent", last_agent_name)

    input_items.append({"role": "system", "content": output})
    ctx.set(INPUT_ITEMS, input_items)
    return output