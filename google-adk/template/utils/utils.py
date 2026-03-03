import os
from http.client import responses

import httpx
import restate

from pydantic import BaseModel


class WeatherPrompt(BaseModel):
    user_id: str = "user-123"
    session_id: str = "session-123"
    message: str = "What is the weather like in San Francisco?"


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
    return WeatherResponse(temperature=23, description=f"Sunny and warm.")


# <end_weather>


def fail_on_denver(city):
    if city == "Denver":
        raise Exception("[👻 SIMULATED] Fetching weather failed: Weather API down...")
