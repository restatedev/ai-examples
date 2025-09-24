import restate
from agents import Agent, RunConfig, Runner, function_tool, RunContextWrapper

from app.middleware import DurableModelCalls
from app.utils import (
    HotelBooking,
    FlightBooking,
    CarBooking,
    reserve_hotel,
    reserve_flight,
    reserve_car,
    BookingRequest,
)


@function_tool
async def book_hotel(
    wrapper: RunContextWrapper[restate.Context], booking: HotelBooking
) -> dict:
    """Book a hotel reservation with durable execution."""
    restate_context = wrapper.context
    result = await restate_context.run_typed("Book hotel", reserve_hotel, booking=booking)
    return result.model_dump()


@function_tool
async def book_flight(
    wrapper: RunContextWrapper[restate.Context], booking: FlightBooking
) -> dict:
    """Book a flight with durable execution."""
    restate_context = wrapper.context
    result = await restate_context.run_typed("Book flight", reserve_flight, booking=booking)
    return result.model_dump()


@function_tool
async def book_car(
    wrapper: RunContextWrapper[restate.Context], booking: CarBooking
) -> dict:
    """Book a car rental with durable execution."""
    restate_context = wrapper.context
    result = await restate_context.run_typed("Book car", reserve_car, booking=booking)
    return result.model_dump()


booking_agent = Agent[restate.Context](
    name="BookingWithRollbackAgent",
    instructions="You are a travel booking agent that can book hotels, flights, and cars. If any booking fails, the system will handle rollback automatically through Restate's durable execution.",
    tools=[book_hotel, book_flight, book_car],
)


agent_service = restate.Service("BookingWithRollbackAgent")


@agent_service.handler()
async def book(restate_context: restate.Context, message: str) -> str:
    result = await Runner.run(
        booking_agent,
        input=message,
        context=restate_context,
        run_config=RunConfig(
            model="gpt-4o", model_provider=DurableModelCalls(restate_context)
        ),
    )

    return result.final_output