import agents
import restate
from pydantic import BaseModel, ConfigDict
from agents import Agent, function_tool, handoff, RunContextWrapper, RunConfig
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX

from openai_sdk.middleware import RestateModelProvider
from openai_sdk.utils import retrieve_flight_info, send_invoice, update_seat_in_booking_system

"""
This example shows how to turn the OpenAI SDK example into a resilient Restate agent.

The example is a customer service agent for an airline that can send invoices and update seat bookings.
This is an OpenAI SDK example that has been adapted to use Restate for resiliency and workflow guarantees:
https://github.com/openai/openai-agents-python/blob/main/examples/customer_service/main.py
"""


# To have access to the Restate context in the tools, we can pass it along in the context that we pass to the tools
class ToolContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    restate_context: restate.ObjectContext
    customer_id: str | None = None


# TOOLS


@function_tool
async def update_seat(
    context: RunContextWrapper[ToolContext],
    confirmation_number: str,
    new_seat: str,
) -> str:
    """
    Update the seat for a given confirmation number.

    Args:
        confirmation_number: The confirmation number for the flight.
        new_seat: The new seat to update to.
    """

    # Do durable steps in your tools by using the Restate context
    ctx = context.context.restate_context

    # 1. Look up the flight using the confirmation number
    flight = await ctx.run(
        "Info lookup", retrieve_flight_info, args=(confirmation_number,)
    )

    # 2. Update the seat in the booking system
    success = await ctx.run(
        "Update seat",
        update_seat_in_booking_system,
        args=(confirmation_number, new_seat, flight),
    )

    if not success:
        return f"Failed to update seat for confirmation number {confirmation_number}."
    return f"Updated seat to {new_seat} for confirmation number {confirmation_number}."


@function_tool(
    name_override="invoice_sending_tool",
    description_override="Sends invoices to customers for booked flights.",
)
async def invoice_sending(
    context: RunContextWrapper[ToolContext], confirmation_number: str
):
    # Do durable steps in your tools by using the Restate context
    ctx = context.context.restate_context

    # 1. Look up the flight using the confirmation number
    flight = await ctx.run(
        "Info lookup", retrieve_flight_info, args=(confirmation_number,)
    )

    # 2. Send the invoice to the customer
    await ctx.run("Send invoice", send_invoice, args=(confirmation_number, flight))


### AGENTS

# This is identical to the examples of the OpenAI SDK
faq_agent = Agent[ToolContext](
    name="Invoice Sending Agent",
    handoff_description="A helpful agent that can send invoices.",
    instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
    You are an Invoice Sending agent. If you are speaking to a customer, you probably were transferred to from the triage agent.
    Use the following routine to support the customer.
    # Routine
    1. Identify the last question asked by the customer.
    2. Use the invoice sending tool to send the invoice. 
    3. If you cannot answer the question, transfer back to the triage agent.""",
    tools=[invoice_sending],
)

seat_booking_agent = Agent[ToolContext](
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

triage_agent = Agent[ToolContext](
    model="o3-mini",
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

agent_dict = {
    agent.name: agent for agent in [faq_agent, seat_booking_agent, triage_agent]
}

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
    # Use Restate's K/V store to keep track of the conversation history and last agent
    input_items = await ctx.get(INPUT_ITEMS) or []
    input_items.append({"role": "user", "content": req})
    ctx.set(INPUT_ITEMS, input_items)

    last_agent_name = await ctx.get("agent") or triage_agent.name
    last_agent = agent_dict[last_agent_name]

    # Pass the Restate context to the tools
    tool_context = ToolContext(restate_context=ctx, customer_id=ctx.key())

    result = await agents.Runner.run(
        last_agent,
        input=input_items,
        context=tool_context,
        # Use the RestateModelProvider to persist the LLM calls in Restate
        run_config=RunConfig(model_provider=RestateModelProvider(ctx)),
    )

    ctx.set("agent", result.last_agent.name)

    output = str(result.final_output)
    input_items.append({"role": "system", "content": output})
    ctx.set(INPUT_ITEMS, input_items)
    return output
