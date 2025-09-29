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
    date: str
    amount: float
    category: str
    place_of_service: str
    reason: str


class WeatherRequest(BaseModel):
    """Request to get the weather for a city."""

    city: str


class WeatherResponse(BaseModel):
    """Request to get the weather for a city."""

    temperature: float
    description: str


# Booking-related models


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


class BookingRequest(BaseModel):
    """Booking request data structure."""

    booking_id: str
    hotel: Optional[HotelBooking] = None
    flight: Optional[FlightBooking] = None


class BookingResult(BaseModel):
    """Booking result structure."""

    id: str
    status: str
    details: Dict[str, Any]
