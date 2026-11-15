import logging
import os

import restate
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentInterface,
    AgentSkill,
)
from fastapi import FastAPI

from app.common.a2a.a2a_middleware import RestateA2AMiddleware

from .agent import ADKWeatherAgent, agent_service

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(process)d] [%(levelname)s] - %(message)s",
)
logger = logging.getLogger(__name__)

RESTATE_HOST = os.getenv("RESTATE_HOST", "http://localhost:8080")

AGENT_CARD = AgentCard(
    name="WeatherAgent",
    description="Agent to answer questions about the weather in a city.",
    supported_interfaces=[
        AgentInterface(
            url=RESTATE_HOST, protocol_binding="JSONRPC", protocol_version="1.0"
        )
    ],
    version="1.0.0",
    capabilities=AgentCapabilities(streaming=False, push_notifications=False),
    skills=[
        AgentSkill(
            id="get_weather",
            name="Fetch weather",
            description="Retrieves the current weather report for a specified city.",
            tags=["weather"],
        )
    ],
    default_input_modes=["text", "text/plain"],
    default_output_modes=["text", "text/plain"],
)


WEATHER_AGENT = RestateA2AMiddleware(
    AGENT_CARD,
    ADKWeatherAgent(),
)

app = FastAPI()


@app.get("/.well-known/agent-card.json")
async def agent_json():
    """Serve the agent card"""
    return WEATHER_AGENT.agent_card_json


app.mount("/restate/v1", restate.app([*WEATHER_AGENT, agent_service]))


def main():
    """Serve the agent at a specified port using hypercorn."""
    import asyncio

    import hypercorn.asyncio

    if not (
        os.getenv("GOOGLE_API_KEY")
        or os.getenv("GEMINI_API_KEY")
        or os.getenv("GOOGLE_GENAI_USE_VERTEXAI")
    ):
        raise RuntimeError(
            "Set GOOGLE_API_KEY or GEMINI_API_KEY, or configure Vertex AI."
        )

    conf = hypercorn.Config()
    host = "localhost"
    port = os.getenv("AGENT_PORT", "9080")
    conf.bind = [f"{host}:{port}"]
    logger.info(f"Server running at http://{host}:{port}")
    logger.info("Available endpoints:")
    logger.info(f"  - Agent card: http://{host}:{port}/.well-known/agent-card.json")
    logger.info(f"  - Restate services: http://{host}:{port}/restate/v1")
    asyncio.run(hypercorn.asyncio.serve(app, conf))


if __name__ == "__main__":
    main()
