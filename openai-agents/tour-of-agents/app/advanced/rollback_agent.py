from typing import Callable, Any

import restate
from agents import Agent, RunConfig, Runner, function_tool, RunContextWrapper
from pydantic import Field
from restate import TerminalError

from app.utils.middleware import DurableModelCalls, raise_restate_errors
from app.utils.models import HotelBooking, FlightBooking, BookingRequest
from app.utils.utils import (
    reserve_hotel,
    reserve_flight,
    cancel_hotel,
    cancel_flight,
)


# Enrich the agent context with a list to track rollback actions
class BookingContext:
    booking_id: str
    restate_context: restate.Context
    on_rollback: list[Callable[Any, Any]] = Field(default=[])


# Functions raise terminal errors instead of feeding them back to the agent
@function_tool(failure_error_function=raise_restate_errors)
async def book_hotel(
    wrapper: RunContextWrapper[BookingContext], booking: HotelBooking
) -> dict:
    """Book a hotel"""
    booking_context = wrapper.context
    restate_context = booking_context.restate_context
    booking_id = booking_context.booking_id

    # Register a rollback action for each step, in case of failures further on in the workflow
    booking_context.on_rollback.append(
        lambda: restate_context.run_typed(
            "Cancel hotel", cancel_hotel, booking_id=booking_id
        )
    )

    # Execute the workflow step
    result = await restate_context.run_typed(
        "Book hotel", reserve_hotel, booking_id=booking_id, booking=booking
    )
    return result.model_dump()


@function_tool(failure_error_function=raise_restate_errors)
async def book_flight(
    wrapper: RunContextWrapper[BookingContext], booking: FlightBooking
) -> dict:
    """Book a flight"""
    booking_context = wrapper.context
    restate_context = booking_context.restate_context
    booking_id = booking_context.booking_id

    booking_context.on_rollback.append(
        lambda: restate_context.run_typed(
            "Cancel flight", cancel_flight, booking_id=booking_id
        )
    )
    result = await restate_context.run_typed(
        "Book flight", reserve_flight, booking_id=booking_id, booking=booking
    )
    return result.model_dump()


# ... Do the same for cars ...


agent_service = restate.Service("BookingWithRollbackAgent")


@agent_service.handler()
async def book(restate_context: restate.Context, message: BookingRequest) -> str:

    booking_context = BookingContext(
        booking_id=message.booking_id, restate_context=restate_context
    )

    booking_agent = Agent[BookingContext](
        name="BookingWithRollbackAgent",
        instructions="Book a complete travel package with the requirements in the prompt."
        "Use the tools to request booking of hotels and flights.",
        tools=[book_hotel, book_flight],
    )

    try:
        result = await Runner.run(
            booking_agent,
            input=message.model_dump_json(),
            context=booking_context,
            run_config=RunConfig(
                model="gpt-4o", model_provider=DurableModelCalls(restate_context)
            ),
        )
    except TerminalError as e:
        # Run all the rollback actions on terminal errors
        for compensation in reversed(booking_context.on_rollback):
            await compensation()
        raise e

    return result.final_output
