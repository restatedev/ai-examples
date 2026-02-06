from pydantic import BaseModel
from restate import TerminalError


class HotelBooking(BaseModel):
    """Hotel booking data structure."""

    name: str
    dates: str
    guests: int


class FlightBooking(BaseModel):
    """Flight booking data structure."""

    origin: str
    destination: str
    date: str
    passengers: int


class BookingPrompt(BaseModel):
    """Booking request data structure."""

    booking_id: str = "booking_123"
    message: str = (
        "I need to book a business trip to San Francisco from March 15-17. Flying from JFK, need a hotel downtown for 1 guest."
    )


class BookingResult(BaseModel):
    """Booking result structure."""

    id: str
    confirmation: str


async def reserve_hotel(id: str, booking: HotelBooking) -> BookingResult:
    """Reserve a hotel (simulated)."""
    print(f"🏨 Reserving hotel in {booking.name} for {booking.guests} guests")
    return BookingResult(
        id=id,
        confirmation=f"Hotel {booking.name} booked for {booking.guests} guests on {booking.dates}",
    )


async def reserve_flight(id: str, booking: FlightBooking) -> BookingResult:
    """Reserve a flight (simulated)."""
    print(f"✈️ Reserving flight from {booking.origin} to {booking.destination}")
    if booking.destination == "San Francisco" or booking.destination == "SFO":
        print(f"[👻 SIMULATED] Flight booking failed: No flights to SFO available...")
        raise TerminalError(
            f"[👻 SIMULATED] Flight booking failed: No flights to SFO available..."
        )
    return BookingResult(
        id=id,
        confirmation=f"Flight from {booking.origin} to {booking.destination} on {booking.date} for {booking.passengers} passengers",
    )


async def cancel_hotel(id: str) -> None:
    """Cancel hotel booking."""
    print(f"❌ Cancelling hotel booking {id}")


async def cancel_flight(id: str) -> None:
    """Cancel flight booking."""
    print(f"❌ Cancelling flight booking {id}")
