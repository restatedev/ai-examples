from typing import Optional, Dict, Any

from pydantic.alias_generators import to_camel as camelize

from pydantic import BaseModel, ConfigDict

# Prompts for AI agents (with default messages)


class ChatMessage(BaseModel):
    message: str = "Which use cases does Restate support?"


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
