import httpx
import restate
from agents import Agent, Runner
from openai.types.chat import ChatCompletionMessage, ChatCompletionAssistantMessageParam
from restate import TerminalError
from restate.ext.openai import DurableRunner

from utils.models import (
    WeatherResponse,
    InsuranceClaim,
    BookingResult,
    FlightBooking,
    HotelBooking,
    WeatherRequest,
)


# <start_weather>
async def fetch_weather(city: str) -> WeatherResponse:
    fail_on_denver(city)
    return f"The weather in {city} is sunny and warm."

# <end_weather>


def fail_on_denver(city):
    if city == "Denver":
        raise Exception("[👻 SIMULATED] Fetching weather failed: Weather API down...")


async def request_human_review(claim: InsuranceClaim, awakeable_id: str) -> None:
    """Simulate requesting human review."""
    print(f"🔔 Human review requested: {claim.model_dump_json()}")
    print(f"  Submit your claim review via: \n ")
    print(
        f"  curl localhost:8080/restate/awakeables/{awakeable_id}/resolve --json 'true'"
    )


async def request_mcp_approval(mcp_tool_name: str, awakeable_id: str) -> None:
    """Simulate requesting human review."""
    print(f"🔔 Human review requested: {mcp_tool_name}")
    print(f"  Submit your mcp tool approval via: \n ")
    print(
        f"  curl localhost:8080/restate/awakeables/{awakeable_id}/resolve --json true"
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
        raise TerminalError(
            f"[👻 SIMULATED] Flight booking failed: No flights to SFO available..."
        )
    return BookingResult(
        id=booking_id,
        confirmation=f"Flight from {booking.origin} to {booking.destination} on {booking.date} for {booking.passengers} passengers",
    )


async def cancel_hotel(booking_id: str) -> None:
    """Cancel hotel booking."""
    print(f"❌ Cancelling hotel booking {booking_id}")


async def cancel_flight(booking_id: str) -> None:
    """Cancel flight booking."""
    print(f"❌ Cancelling flight booking {booking_id}")


# <start_eligibility>
eligibility_agent_service = restate.Service("EligibilityAgent")


@eligibility_agent_service.handler()
async def run_eligibility_agent(_ctx: restate.Context, claim: InsuranceClaim) -> str:
    result = await DurableRunner.run(
        Agent(
            name="EligibilityAgent",
            instructions="Decide whether the following claim is eligible for reimbursement."
            "Respond with eligible if it's a medical claim, and not eligible otherwise.",
        ),
        input=claim.model_dump_json(),
    )
    return result.final_output
# <end_eligibility>


rate_comparison_agent_service = restate.Service("RateComparisonAgent")


@rate_comparison_agent_service.handler()
async def run_rate_comparison_agent(
    _ctx: restate.Context, claim: InsuranceClaim
) -> str:
    result = await DurableRunner.run(
        Agent(
            name="RateComparisonAgent",
            instructions="Decide whether the cost of the claim is reasonable given the treatment."
            + "Respond with reasonable or not reasonable.",
        ),
        input=claim.model_dump_json(),
    )
    return result.final_output


fraud_agent_service = restate.Service("FraudAgent")


@fraud_agent_service.handler()
async def run_fraud_agent(_ctx: restate.Context, claim: InsuranceClaim) -> str:
    result = await DurableRunner.run(
        Agent(
            name="FraudAgent",
            instructions="Decide whether the claim is fraudulent."
            "Always respond with low risk, medium risk, or high risk.",
        ),
        input=claim.model_dump_json(),
    )
    return result.final_output


async def convert_currency(amount: float, source: str, target: str) -> float:
    """Convert currency (placeholder)."""
    return amount


async def process_payment(claim_id: str, amount: float) -> str:
    """Process payment (placeholder)."""
    return f"Payment processed for claim {claim_id}: ${amount}"