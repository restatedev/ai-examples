import httpx


async def fetch_weather(city: str) -> str:
    resp = httpx.get(f"https://wttr.in/{city}?format=j1", timeout=10.0)
    resp.raise_for_status()
    return resp.text


async def parse_weather_data(weather_data: str) -> dict:
    import json

    weather_json = json.loads(weather_data)
    current = weather_json["current_condition"][0]
    return {
        "temperature": current["temp_C"],
        "description": current["weatherDesc"][0]["value"],
    }
