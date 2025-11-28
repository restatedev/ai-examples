from typing import Callable

import restate
from agents import Agent, RunConfig, Runner, RunContextWrapper
from pydantic import Field, BaseModel, ConfigDict
from restate import TerminalError

from app.utils.middleware import Runner, function_tool
from app.utils.models import HotelBooking, FlightBooking, BookingPrompt, BookingResult
from app.utils.utils import (
    reserve_hotel,
    reserve_flight,
    cancel_hotel,
    cancel_flight,
)


# Enrich the agent context with a list to track rollback actions
class BookingContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    booking_id: str
    restate_context: restate.Context
    on_rollback: list[Callable] = Field(default=[])


# Functions raise terminal errors instead of feeding them back to the agent
@function_tool
async def book_hotel(
    wrapper: RunContextWrapper[BookingContext], booking: HotelBooking
) -> BookingResult:
    """Book a hotel"""
    booking_context = wrapper.context

    # Register a rollback action for each step, in case of failures further on in the workflow
    booking_context.on_rollback.append(
        lambda: booking_context.restate_context.run_typed(
            "Cancel hotel", cancel_hotel, booking_id=booking_context.booking_id
        )
    )

    # Execute the workflow step
    return await booking_context.restate_context.run_typed(
        "Book hotel",
        reserve_hotel,
        booking_id=booking_context.booking_id,
        booking=booking,
    )


@function_tool
async def book_flight(
    wrapper: RunContextWrapper[BookingContext], booking: FlightBooking
) -> BookingResult:
    """Book a flight"""
    booking_context = wrapper.context

    booking_context.on_rollback.append(
        lambda: booking_context.restate_context.run_typed(
            "Cancel flight", cancel_flight, booking_id=booking_context.booking_id
        )
    )
    return await booking_context.restate_context.run_typed(
        "Book flight",
        reserve_flight,
        booking_id=booking_context.booking_id,
        booking=booking,
    )


# ... Do the same for cars ...


agent_service = restate.Service("BookingWithRollbackAgent")


@agent_service.handler()
async def book(restate_context: restate.Context, prompt: BookingPrompt) -> str:

    booking_context = BookingContext(
        booking_id=prompt.booking_id, restate_context=restate_context
    )

    booking_agent = Agent[BookingContext](
        name="BookingWithRollbackAgent",
        instructions="Book a complete travel package with the requirements in the prompt."
        "Use tools to first book the hotel, then the flight.",
        tools=[book_hotel, book_flight],
    )

    try:
        result = await Runner.run(booking_agent, input=prompt.message)
    except TerminalError as e:
        # Run all the rollback actions on terminal errors
        for compensation in reversed(booking_context.on_rollback):
            await compensation()
        raise e

    return result.final_output
