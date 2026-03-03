import os
from http.client import responses

import httpx
import restate

from pydantic import BaseModel


class WeatherPrompt(BaseModel):
    """Request to get the weather for a city."""

    message: str = "What is the weather in Detroit?"


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
    return f"The weather in {city} is sunny and warm."


# <end_weather>


def fail_on_denver(city):
    if city == "Denver":
        raise Exception("[👻 SIMULATED] Fetching weather failed: Weather API down...")
