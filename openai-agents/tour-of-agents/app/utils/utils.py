import httpx
import restate
from typing import Dict, Any

from app.utils.models import WeatherResponse, InsuranceClaim, BookingResult, FlightBooking, HotelBooking


# <start_weather>
async def fetch_weather(city: str) -> WeatherResponse:
    fail_on_denver(city)
    weather_data = await call_weather_api(city)
    return parse_weather_data(weather_data)


# <end_weather>


def fail_on_denver(city):
    if city == "Denver":
        raise Exception("[👻 SIMULATED] Fetching weather failed: Weather API down...")


async def call_weather_api(city):
    try:
        resp = httpx.get(f"https://wttr.in/{httpx.URL(city)}?format=j1", timeout=10.0)
        resp.raise_for_status()

        if resp.text.startswith("Unknown location"):
            raise restate.TerminalError(
                f"Unknown location: {city}. Please provide a valid city name."
            )

        return resp.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise restate.TerminalError(
                f"City not found: {city}. Please provide a valid city name."
            ) from e
        else:
            raise Exception(f"HTTP error occurred: {e}") from e


def parse_weather_data(weather_data: dict) -> WeatherResponse:
    # weather_json = json.loads(weather_data)
    current = weather_data["current_condition"][0]
    return WeatherResponse(
        temperature=float(current["temp_C"]),
        description=current["weatherDesc"][0]["value"],
    )



async def request_human_review(message: str, awakeable_id: str) -> None:
    """Simulate requesting human review."""
    print(f"🔔 Human review requested: {message}")
    print(f"   Awakeable ID: {awakeable_id}")
    print("   [In a real system, this would notify a human reviewer]")


# Additional utility functions for parallel processing
async def check_eligibility(claim: InsuranceClaim) -> Dict[str, Any]:
    """Check claim eligibility (simplified version)."""
    return {
        "eligible": claim.amount <= 10000,
        "reason": "Within standard limits" if claim.amount <= 10000 else "Exceeds maximum coverage",
        "score": min(100, max(0, 100 - (claim.amount / 100)))
    }


async def compare_to_standard_rates(claim: InsuranceClaim) -> Dict[str, Any]:
    """Compare claim to standard rates (simplified version)."""
    standard_rate = 500.0  # Simplified standard rate
    ratio = claim.amount / standard_rate

    return {
        "standard_rate": standard_rate,
        "claim_amount": claim.amount,
        "ratio": ratio,
        "assessment": "within_normal" if ratio <= 2.0 else "above_normal" if ratio <= 5.0 else "exceptional"
    }


async def check_fraud(claim: InsuranceClaim) -> Dict[str, Any]:
    """Check for fraud indicators (simplified version)."""
    # Simple fraud detection based on claim characteristics
    risk_score = 0

    if claim.amount > 5000:
        risk_score += 30
    if "urgent" in claim.description.lower():
        risk_score += 20
    if len(claim.description) < 10:
        risk_score += 25

    return {
        "risk_score": risk_score,
        "risk_level": "low" if risk_score < 25 else "medium" if risk_score < 50 else "high",
        "indicators": []
    }





async def reserve_hotel(booking_id: str, booking: HotelBooking) -> BookingResult:
    """Reserve a hotel (simulated)."""
    import uuid
    booking_id = str(uuid.uuid4())
    print(f"🏨 Reserving hotel in {booking.location} for {booking.guests} guests")

    # Simulate potential failure for certain locations
    if booking.location.lower() == "atlantis":
        raise Exception(f"[👻 SIMULATED] Hotel booking failed: No hotels available in {booking.location}")

    return BookingResult(
        id=booking_id,
        status="reserved",
        details={
            "location": booking.location,
            "checkin": booking.checkin_date,
            "checkout": booking.checkout_date,
            "guests": booking.guests,
            "room_type": booking.room_type
        }
    )


async def reserve_flight(booking_id: str, booking: FlightBooking) -> BookingResult:
    """Reserve a flight (simulated)."""
    import uuid
    booking_id = str(uuid.uuid4())
    print(f"✈️ Reserving flight from {booking.origin} to {booking.destination}")

    # Simulate potential failure for certain routes
    if booking.origin.lower() == booking.destination.lower():
        raise Exception(f"[👻 SIMULATED] Flight booking failed: Origin and destination cannot be the same")

    return BookingResult(
        id=booking_id,
        status="reserved",
        details={
            "origin": booking.origin,
            "destination": booking.destination,
            "departure": booking.departure_date,
            "return": booking.return_date,
            "passengers": booking.passengers,
            "class": booking.class_type
        }
    )


async def confirm_hotel(booking_id: str) -> str:
    """Confirm hotel booking."""
    print(f"✅ Confirming hotel booking {booking_id}")
    return f"Hotel booking {booking_id} confirmed"


async def confirm_flight(booking_id: str) -> str:
    """Confirm flight booking."""
    print(f"✅ Confirming flight booking {booking_id}")
    return f"Flight booking {booking_id} confirmed"


async def cancel_hotel(booking_id: str) -> None:
    """Cancel hotel booking."""
    print(f"❌ Cancelling hotel booking {booking_id}")


async def cancel_flight(booking_id: str) -> None:
    """Cancel flight booking."""
    print(f"❌ Cancelling flight booking {booking_id}")

