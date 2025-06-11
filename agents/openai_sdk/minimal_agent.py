import uuid
import agents
import restate
from pydantic import BaseModel, ConfigDict
from agents import (
    Agent,
    function_tool,
    RunContextWrapper,
)
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX

from openai_sdk.middleware import RestateModelWrapper


class AirlineAgentContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    restate_context: restate.ObjectContext
    passenger_name: str | None = None
    confirmation_number: str | None = None
    seat_number: str | None = None
    flight_number: str | None = None


# TOOLS


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
    my_uuid = await context.context.restate_context.run("Generate seat uuid", lambda: uuid.uuid4().hex)
    context.context.confirmation_number = confirmation_number
    context.context.seat_number = new_seat
    return f"Updated seat to {new_seat} for confirmation number {confirmation_number}. My seat uuid is {my_uuid}."


### AGENTS

seat_booking_agent = Agent[AirlineAgentContext](
    model=RestateModelWrapper,
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


agent_dict = {
    agent.name: agent for agent in [seat_booking_agent]
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

    input_items = await ctx.get(INPUT_ITEMS) or []
    input_items.append({"role": "user", "content": req})
    ctx.set(INPUT_ITEMS, input_items)

    last_agent_name = await ctx.get("agent") or seat_booking_agent.name
    last_agent = agent_dict[last_agent_name]

    result = await agents.Runner.run(
        last_agent, input=input_items, context=AirlineAgentContext(
            restate_context=ctx,
            passenger_name="John Doe",
            confirmation_number="12345",
            seat_number="12A",
            flight_number="AA123",
        ),
        run_config=agents.RunConfig(model=RestateModelWrapper(ctx))
    )

    output, last_agent_name = str(result.final_output), result.last_agent.name
    ctx.set("agent", last_agent_name)

    input_items.append({"role": "system", "content": output})
    ctx.set(INPUT_ITEMS, input_items)
    return output
