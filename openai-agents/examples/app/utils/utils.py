from restate import TerminalError

from app.utils.models import (
    BookingResult,
    FlightBooking,
    HotelBooking,
)


async def request_mcp_approval(mcp_tool_name: str, awakeable_id: str) -> None:
    """Simulate requesting human review."""
    print(f"🔔 Human review requested: {mcp_tool_name}")
    print(f"  Submit your mcp tool approval via: \n ")
    print(
        f"  curl localhost:8080/restate/awakeables/{awakeable_id}/resolve --json true"
    )


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
