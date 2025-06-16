import restate
import os
from agent import CurrencyAgent
from fastapi import FastAPI

from a2a.common.a2a_middleware import AgentMiddleware
from a2a.common.models import MissingAPIKeyError, AgentCapabilities, AgentCard, AgentSkill
from dotenv import load_dotenv


load_dotenv()

RESTATE_HOST = os.getenv("RESTATE_HOST", "http://localhost:8080")

AGENT_CARD = AgentCard(
    name="CurrencyAgent",
    description="Helps with exchange rates for currencies",
    url=RESTATE_HOST,
    version="1.0.0",
    defaultInputModes=CurrencyAgent.SUPPORTED_CONTENT_TYPES,
    defaultOutputModes=CurrencyAgent.SUPPORTED_CONTENT_TYPES,
    capabilities=AgentCapabilities(streaming=False, pushNotifications=False),
    skills=[
        AgentSkill(
            id="convert_currency",
            name="Currency Exchange Rates Tool",
            description="Helps with exchange values between various currencies",
            tags=["currency conversion", "currency exchange"],
            examples=["What is exchange rate between USD and GBP?"],
        )
    ],
)

CURRENCY_EXCHANGE_AGENT = AgentMiddleware(AGENT_CARD, CurrencyAgent())

app = FastAPI()


@app.get("/.well-known/agent.json")
async def agent_json():
    """Serve the agent card"""
    return CURRENCY_EXCHANGE_AGENT.agent_card_json


app.mount("/restate/v1", restate.app(CURRENCY_EXCHANGE_AGENT))


def main():
    """Starts the Currency Agent server."""
    import asyncio
    import hypercorn.asyncio

    if not os.getenv("GOOGLE_API_KEY"):
        raise MissingAPIKeyError("GOOGLE_API_KEY environment variable not set.")

    port = os.getenv("AGENT_PORT", "9082")
    conf = hypercorn.Config()
    conf.bind = [f"0.0.0.0:{port}"]
    asyncio.run(hypercorn.asyncio.serve(app, conf))


if __name__ == "__main__":
    main()
