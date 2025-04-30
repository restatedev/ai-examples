from common.server.a2a_server import a2a_services
from common.types import AgentCard, AgentCapabilities, AgentSkill, MissingAPIKeyError
from agents.langgraph.agent import CurrencyAgent
import hypercorn
import asyncio
import restate
import os
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

RESTATE_HOST = os.getenv("RESTATE_HOST", "http://localhost:8080")
AGENT_HOST = os.getenv("AGENT_HOST", "0.0.0.0:9083")


def main():
    """Starts the Currency Agent server."""
    try:
        if not os.getenv("GOOGLE_API_KEY"):
            raise MissingAPIKeyError("GOOGLE_API_KEY environment variable not set.")

        capabilities = AgentCapabilities(streaming=False, pushNotifications=False)
        skill = AgentSkill(
            id="convert_currency",
            name="Currency Exchange Rates Tool",
            description="Helps with exchange values between various currencies",
            tags=["currency conversion", "currency exchange"],
            examples=["What is exchange rate between USD and GBP?"],
        )
        agent_name = "CurrencyAgent"
        agent_card = AgentCard(
            name=agent_name,
            description="Helps with exchange rates for currencies",
            url=f"{RESTATE_HOST}/{agent_name}A2AServer/process_request",
            version="1.0.0",
            defaultInputModes=CurrencyAgent.SUPPORTED_CONTENT_TYPES,
            defaultOutputModes=CurrencyAgent.SUPPORTED_CONTENT_TYPES,
            capabilities=capabilities,
            skills=[skill],
        )

        services = a2a_services(
            agent_name=agent_name,
            agent_card=agent_card,
            agent=CurrencyAgent(),
        )

        app = restate.app(services=services)

        conf = hypercorn.Config()
        conf.bind = [AGENT_HOST]
        asyncio.run(hypercorn.asyncio.serve(app, conf))
    except MissingAPIKeyError as e:
        logger.error(f"Error: {e}")
        exit(1)
    except Exception as e:
        logger.error(f"An error occurred during server startup: {e}")
        exit(1)


if __name__ == "__main__":
    main()
