import restate

from typing import Callable
from agents import Agent, RunContextWrapper
from pydantic import Field, BaseModel, ConfigDict
from restate.ext.openai import restate_context, DurableRunner, durable_function_tool

from utils import (
    HotelBooking, FlightBooking, BookingPrompt, BookingResult,
    reserve_hotel, reserve_flight, cancel_hotel, cancel_flight,
)


# Enrich the agent context with a list to track rollback actions
class BookingContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    booking_id: str
    on_rollback: list[Callable] = Field(default=[])


# Functions raise terminal errors instead of feeding them back to the agent
@durable_function_tool
async def book_hotel(
    wrapper: RunContextWrapper[BookingContext], booking: HotelBooking
) -> BookingResult:
    """Book a hotel"""
    ctx = restate_context()
    booking_ctx, booking_id = wrapper.context, wrapper.context.booking_id
    # Register a rollback action for each step, in case of failures further on in the workflow
    booking_ctx.on_rollback.append(
        lambda: ctx.run_typed("🏨 Cancel hotel", cancel_hotel, id=booking_id)
    )

    # Execute the workflow step
    return await ctx.run_typed(
        "🏨 Book hotel", reserve_hotel, id=booking_id, booking=booking
    )


@durable_function_tool
async def book_flight(
    wrapper: RunContextWrapper[BookingContext], booking: FlightBooking
) -> BookingResult:
    """Book a flight"""
    ctx = restate_context()
    booking_ctx, booking_id = wrapper.context, wrapper.context.booking_id
    booking_ctx.on_rollback.append(
        lambda: ctx.run_typed("✈️ Cancel flight", cancel_flight, id=booking_id)
    )
    return await ctx.run_typed(
        "✈️ Book flight", reserve_flight, id=booking_id, booking=booking
    )


# ... Do the same for cars ...


agent = Agent[BookingContext](
    name="BookingWithRollbackAgent",
    instructions="Book a complete travel package with the requirements in the prompt."
    "Use tools to first book the hotel, then the flight.",
    tools=[book_hotel, book_flight],
)


agent_service = restate.Service("BookingWithRollbackAgent")


@agent_service.handler()
async def book(_ctx: restate.Context, req: BookingPrompt) -> str:
    booking_ctx = BookingContext(booking_id=req.booking_id)
    try:
        result = await DurableRunner.run(agent, req.message, context=booking_ctx)
    except restate.TerminalError as e:
        # Run all the rollback actions on terminal errors
        for compensation in reversed(booking_ctx.on_rollback):
            await compensation()
        raise e

    return result.final_output
