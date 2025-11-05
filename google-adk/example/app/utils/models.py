from typing import Optional, Dict, Any

from pydantic.alias_generators import to_camel as camelize

from pydantic import BaseModel, ConfigDict

# Prompts for AI agents (with default messages)


class WeatherPrompt(BaseModel):
    message: str = "What is the weather like in San Francisco?"


class ClaimPrompt(BaseModel):
    message: str = "Process my hospital bill of 3000USD for a broken leg."


class ChatMessage(BaseModel):
    message: str = "Make a poem about durable execution."


class InsuranceClaim(BaseModel):
    """Insurance claim data structure."""

    model_config = ConfigDict(populate_by_name=True, alias_generator=camelize)
    date: str = "2024-10-01"
    amount: float = 3000
    category: str = "orthopedic"
    place_of_service: str = "General Hospital"
    reason: str = "hospital bill for a broken leg"


class WeatherRequest(BaseModel):
    """Request to get the weather for a city."""

    model_config = ConfigDict(extra="forbid")
    city: str


class WeatherResponse(BaseModel):
    """Request to get the weather for a city."""

    temperature: float
    description: str


# Booking-related models


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
