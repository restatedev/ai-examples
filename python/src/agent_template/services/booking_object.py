import restate

from restate.serde import PydanticJsonSerde
from pydantic import BaseModel

from src.agent_template.services.seat_object import reserve, unreserve


class Booking(BaseModel):
    """
    This represents a booking for a flight for a passenger.

    The passenger_name is the full name of the passenger.
    The passenger_email is the email address of the passenger to send communication.
    The confirmation_number is the confirmation number of the flight.
    The seat_number is the seat number of the passenger.
    The flight_number is the flight number.
    """

    confirmation_number: str
    flight_number: str
    passenger_name: str
    passenger_email: str
    seat_number: str


booking_object_context = (
    "This tool is part of a virtual object that represents a booking for a flight for a passenger."
    "The Virtual Object is keyed by booking ID."
)
booking_object = restate.VirtualObject("BookingObject")


@booking_object.handler()
async def update_seat(ctx: restate.ObjectContext, new_seat_number: str) -> str:
    f"""
    Update the seat for a given customer.
    
    {booking_object_context}

    Args:
        new_seat_number: The new seat to update to.
    """
    booking: Booking = await get_info(ctx)
    success = await ctx.object_call(
        reserve, key=f"{booking.flight_number}-{new_seat_number}", arg=None
    )
    if not success:
        return f"Seat {new_seat_number} is not available"
    else:
        await ctx.object_call(
            unreserve, key=f"{booking.flight_number}-{booking.seat_number}", arg=None
        )
        booking.seat_number = new_seat_number
        ctx.set("booking", booking, PydanticJsonSerde(Booking))
        return f"Seat updated to {new_seat_number}"


@booking_object.handler(kind="shared")
async def send_invoice(ctx: restate.ObjectContext) -> str:
    f"""
    This tool sends an invoice to a customer.

    {booking_object_context}
    """
    booking: Booking = await get_info(ctx)
    print(f"Sending invoice to {booking.passenger_name} at {booking.passenger_email}")
    # Send invoice logic here
    return f"Invoice sent to {booking.passenger_name} at {booking.passenger_email}"


@booking_object.handler(kind="shared")
async def get_info(ctx: restate.ObjectContext) -> Booking:
    f"""
    This tool gets the booking information.

    {booking_object_context}
    """
    return await ctx.get("booking", PydanticJsonSerde(Booking)) or Booking(
        confirmation_number="12345",
        flight_number="FL-123",
        passenger_email="alice@gmail.com",
        passenger_name="Alice",
        seat_number="2B",
    )
