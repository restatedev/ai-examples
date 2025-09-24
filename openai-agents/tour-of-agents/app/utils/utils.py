import httpx
import restate
from openai import OpenAI
from typing import Dict, Any, List, Optional
from pydantic import BaseModel


class InsuranceClaim(BaseModel):
    """Insurance claim data structure."""
    id: str
    amount: float
    description: str
    claimant: str


class WeatherRequest(BaseModel):
    """Request to get the weather for a city."""

    city: str


class WeatherResponse(BaseModel):
    """Request to get the weather for a city."""

    temperature: float
    description: str


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


def get_openai_client() -> OpenAI:
    """Get OpenAI client with environment configuration."""
    return OpenAI()


class DurableOpenAIWrapper:
    """Wrapper for OpenAI client with Restate durability."""

    def __init__(self, ctx: restate.Context, max_retries: int = 3):
        self.ctx = ctx
        self.max_retries = max_retries
        self.client = get_openai_client()

    async def chat_completions_create(self, **kwargs):
        """Create chat completion with durability."""
        return await self.ctx.run_typed(
            "openai-chat-completion",
            self._create_chat_completion,
            **kwargs
        )

    def _create_chat_completion(self, **kwargs):
        """Internal method to create chat completion."""
        return self.client.chat.completions.create(**kwargs)


# Agent service stubs for multi-agent orchestration
class EligibilityAgent:
    """Eligibility analysis agent."""

    async def run(self, ctx: restate.Context, claim: InsuranceClaim) -> str:
        """Analyze claim eligibility."""
        client = DurableOpenAIWrapper(ctx)

        response = await client.chat_completions_create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an eligibility analysis agent for insurance claims. Analyze the claim and provide a detailed eligibility assessment."},
                {"role": "user", "content": f"Analyze this claim for eligibility: {claim.model_dump_json()}"}
            ]
        )

        return response.choices[0].message.content


class FraudCheckAgent:
    """Fraud detection agent."""

    async def run(self, ctx: restate.Context, claim: InsuranceClaim) -> str:
        """Check claim for potential fraud."""
        client = DurableOpenAIWrapper(ctx)

        response = await client.chat_completions_create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a fraud detection agent for insurance claims. Analyze the claim for potential fraud indicators."},
                {"role": "user", "content": f"Analyze this claim for fraud: {claim.model_dump_json()}"}
            ]
        )

        return response.choices[0].message.content


class RateComparisonAgent:
    """Rate comparison agent."""

    async def run(self, ctx: restate.Context, claim: InsuranceClaim) -> str:
        """Compare claim costs to standard rates."""
        client = DurableOpenAIWrapper(ctx)

        response = await client.chat_completions_create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a rate comparison agent for insurance claims. Compare the claim amount to standard rates and provide cost analysis."},
                {"role": "user", "content": f"Analyze cost for this claim: {claim.model_dump_json()}"}
            ]
        )

        return response.choices[0].message.content


# Global agent instances
eligibility_agent = EligibilityAgent()
fraud_check_agent = FraudCheckAgent()
rate_comparison_agent = RateComparisonAgent()


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



# Booking-related models and functions for advanced examples

class HotelBooking(BaseModel):
    """Hotel booking data structure."""
    location: str
    checkin_date: str
    checkout_date: str
    guests: int
    room_type: str = "standard"


class FlightBooking(BaseModel):
    """Flight booking data structure."""
    origin: str
    destination: str
    departure_date: str
    return_date: Optional[str] = None
    passengers: int
    class_type: str = "economy"


class CarBooking(BaseModel):
    """Car rental booking data structure."""
    location: str
    pickup_date: str
    return_date: str
    car_type: str = "compact"

class BookingRequest(BaseModel):
    """Booking request data structure."""
    hotel: Optional[HotelBooking] = None
    flight: Optional[FlightBooking] = None
    car: Optional[CarBooking] = None


class BookingResult(BaseModel):
    """Booking result structure."""
    id: str
    status: str
    details: Dict[str, Any]


async def reserve_hotel(booking: HotelBooking) -> BookingResult:
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


async def reserve_flight(booking: FlightBooking) -> BookingResult:
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


async def reserve_car(booking: CarBooking) -> BookingResult:
    """Reserve a car (simulated)."""
    import uuid
    booking_id = str(uuid.uuid4())
    print(f"🚗 Reserving {booking.car_type} car in {booking.location}")

    return BookingResult(
        id=booking_id,
        status="reserved",
        details={
            "location": booking.location,
            "pickup": booking.pickup_date,
            "return": booking.return_date,
            "car_type": booking.car_type
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


async def confirm_car(booking_id: str) -> str:
    """Confirm car booking."""
    print(f"✅ Confirming car booking {booking_id}")
    return f"Car booking {booking_id} confirmed"


async def cancel_hotel(booking_id: str) -> str:
    """Cancel hotel booking."""
    print(f"❌ Cancelling hotel booking {booking_id}")
    return f"Hotel booking {booking_id} cancelled"


async def cancel_flight(booking_id: str) -> str:
    """Cancel flight booking."""
    print(f"❌ Cancelling flight booking {booking_id}")
    return f"Flight booking {booking_id} cancelled"


async def cancel_car(booking_id: str) -> str:
    """Cancel car booking."""
    print(f"❌ Cancelling car booking {booking_id}")
    return f"Car booking {booking_id} cancelled"
