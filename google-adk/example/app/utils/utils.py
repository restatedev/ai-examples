import json

import httpx
import restate
from restate import TerminalError

from app.utils.models import (
    WeatherResponse,
    InsuranceClaim,
    BookingResult,
    FlightBooking,
    HotelBooking,
)


# <start_weather>
async def fetch_weather(city: str) -> WeatherResponse:
    # fail_on_denver(city)
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
    current = weather_data["current_condition"][0]
    return WeatherResponse(
        temperature=float(current["temp_C"]),
        description=current["weatherDesc"][0]["value"],
    )


async def request_human_review(claim: InsuranceClaim, awakeable_id: str) -> None:
    """Simulate requesting human review."""
    print(f"🔔 Human review requested: {claim.model_dump_json()}")
    print(f"  Submit your claim review via: \n ")
    print(
        f"  curl localhost:8080/restate/awakeables/{awakeable_id}/resolve --json 'true'"
    )


# Additional utility functions for parallel processing
async def check_eligibility(claim: InsuranceClaim) -> str:
    """Check claim eligibility (simplified version)."""
    return "eligible"


async def compare_to_standard_rates(claim: InsuranceClaim) -> str:
    """Compare claim to standard rates (simplified version)."""
    return "reasonable"


async def check_fraud(claim: InsuranceClaim) -> str:
    """Check for fraud indicators (simplified version)."""
    # Simple fraud detection based on claim characteristics
    return "low risk"

async def reserve_hotel(booking_id: str, booking: HotelBooking) -> BookingResult:
    """Reserve a hotel (simulated)."""
    print(f"🏨 Reserving hotel in {booking.name} for {booking.guests} guests")
    return BookingResult(
        id=booking_id,
        confirmation=f"Hotel {booking.name} booked for {booking.guests} guests on {booking.dates}",
    )


async def reserve_flight(booking_id: str, booking: FlightBooking) -> BookingResult:
    """Reserve a flight (simulated)."""
    print(f"✈️ Reserving flight from {booking.origin} to {booking.destination}")
    if booking.destination == "San Francisco" or booking.destination == "SFO":
        print(f"[👻 SIMULATED] Flight booking failed: No flights to SFO available...")
        raise TerminalError(f"[👻 SIMULATED] Flight booking failed: No flights to SFO available...")
    return BookingResult(
        id=booking_id,
        confirmation=f"Flight from {booking.origin} to {booking.destination} on {booking.date} for {booking.passengers} passengers"
    )

async def cancel_hotel(booking_id: str) -> None:
    """Cancel hotel booking."""
    print(f"❌ Cancelling hotel booking {booking_id}")


async def cancel_flight(booking_id: str) -> None:
    """Cancel flight booking."""
    print(f"❌ Cancelling flight booking {booking_id}")


eligibility_agent_service = restate.Service("EligibilityAgent")

@eligibility_agent_service.handler()
async def run_eligibility_agent(
    restate_context: restate.Context, claim: InsuranceClaim
) -> str:
    result = await Runner.run(
        Agent(
            name="EligibilityAgent",
            instructions="Decide whether the following claim is eligible for reimbursement."
            "Respond with eligible if it's a medical claim, and not eligible otherwise.",
        ),
        input=claim.model_dump_json(),
        run_config=RunConfig(
            model="gpt-4o",
            model_provider=DurableModelCalls(restate_context),
            model_settings=ModelSettings(parallel_tool_calls=False),
        ),
    )
    return result.final_output

rate_comparison_agent_service = restate.Service("RateComparisonAgent")

@rate_comparison_agent_service.handler()
async def run_rate_comparison_agent(
    restate_context: restate.Context, claim: InsuranceClaim
) -> str:
    result = await Runner.run(
        Agent(
            name="RateComparisonAgent",
            instructions="Decide whether the cost of the claim is reasonable given the treatment." +
            "Respond with reasonable or not reasonable.",
        ),
        input=claim.model_dump_json(),
        run_config=RunConfig(
            model="gpt-4o",
            model_provider=DurableModelCalls(restate_context),
            model_settings=ModelSettings(parallel_tool_calls=False),
        ),
    )
    return result.final_output

fraud_agent_service = restate.Service("FraudAgent")

@fraud_agent_service.handler()
async def run_fraud_agent(
    restate_context: restate.Context, claim: InsuranceClaim
) -> str:
    result = await Runner.run(
        Agent(
            name="FraudAgent",
            instructions="Decide whether the cost of the claim is reasonable given the treatment."
            "Respond with reasonable or not reasonable.",
        ),
        input=claim.model_dump_json(),
        run_config=RunConfig(
            model="gpt-4o",
            model_provider=DurableModelCalls(restate_context),
            model_settings=ModelSettings(parallel_tool_calls=False),
        ),
    )
    return result.final_output