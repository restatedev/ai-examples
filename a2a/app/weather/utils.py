import restate
import httpx

from pydantic import BaseModel, ConfigDict


class WeatherPrompt(BaseModel):
    message: str = "What is the weather like in San Francisco?"

class WeatherRequest(BaseModel):
    """Request to get the weather for a city."""

    model_config = ConfigDict(extra="forbid")
    city: str

class WeatherResponse(BaseModel):
    """Request to get the weather for a city."""

    temperature: float
    description: str

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