# pylint: disable=C0116
"""Main entry point for hybrid reimbursement agent."""

import logging
import os
import click
from fastapi import FastAPI
from dotenv import load_dotenv

from agent import HybridReimbursementAgent
from a2a_samples.common.a2a.models import MissingAPIKeyError

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(process)d] [%(levelname)s] - %(message)s",
)
logger = logging.getLogger(__name__)


@click.command()
@click.option('--host', default='localhost', help='Host to bind the server to')
@click.option('--port', default=9083, help='Port to bind the server to')
@click.option(
    '--mode',
    type=click.Choice(['traditional', 'hybrid', 'pure-a2a']),
    default='hybrid',
    help='Server mode: traditional (Restate only), hybrid (ADK+Restate), pure-a2a (SDK only)'
)
def main(host: str, port: int, mode: str):
    """Run the hybrid reimbursement agent in different modes."""
    try:
        # Check for required API keys
        if not os.getenv('OPENAI_API_KEY') and not os.getenv('GEMINI_API_KEY'):
            if not os.getenv('GOOGLE_GENAI_USE_VERTEXAI') == 'TRUE':
                raise MissingAPIKeyError(
                    'Either OPENAI_API_KEY or GEMINI_API_KEY must be set, '
                    'or GOOGLE_GENAI_USE_VERTEXAI must be TRUE.'
                )

        # Create the hybrid agent
        hybrid_agent = HybridReimbursementAgent()

        if mode == 'traditional':
            logger.info("Starting in TRADITIONAL mode (Restate A2A middleware)")
            run_traditional_mode(hybrid_agent, host, port)

        elif mode == 'hybrid':
            logger.info("Starting in HYBRID mode (Google ADK + Restate)")
            run_hybrid_mode(hybrid_agent, host, port)

        elif mode == 'pure-a2a':
            logger.info("Starting in PURE A2A mode (Google SDK only)")
            run_pure_a2a_mode(hybrid_agent, host, port)

    except MissingAPIKeyError as e:
        logger.error(f'Error: {e}')
        exit(1)
    except Exception as e:
        logger.error(f'An error occurred during server startup: {e}')
        exit(1)


def run_traditional_mode(hybrid_agent: HybridReimbursementAgent, host: str, port: int):
    """Run using traditional Restate A2A middleware."""
    import restate
    import asyncio
    import hypercorn.asyncio

    # Get traditional middleware
    middleware = hybrid_agent.get_traditional_middleware()

    app = FastAPI()

    @app.get("/.well-known/agent.json")
    async def agent_json():
        """Serve the agent card"""
        return middleware.agent_card_json

    app.mount("/restate/v1", restate.app(middleware))

    conf = hypercorn.Config()
    conf.bind = [f"{host}:{port}"]
    logger.info(f"Traditional mode server running at http://{host}:{port}")
    asyncio.run(hypercorn.asyncio.serve(app, conf))


def run_hybrid_mode(hybrid_agent: HybridReimbursementAgent, host: str, port: int):
    """Run using hybrid middleware (A2A SDK + Restate)."""
    import restate
    import asyncio
    import hypercorn.asyncio

    # Get hybrid middleware
    middleware = hybrid_agent.get_hybrid_middleware()

    app = FastAPI()

    @app.get("/.well-known/agent.json")
    async def agent_json():
        """Serve the agent card in A2A SDK format"""
        return middleware.agent_card_json

    # Mount both A2A SDK endpoints and Restate endpoints
    app.mount("/restate/v1", restate.app(middleware))

    # You could also mount A2A SDK application here if needed
    # a2a_app = middleware.create_a2a_application(host, port)
    # app.mount("/a2a", a2a_app.build())

    conf = hypercorn.Config()
    conf.bind = [f"{host}:{port}"]
    logger.info(f"Hybrid mode server running at http://{host}:{port}")
    logger.info("Available endpoints:")
    logger.info(f"  - Agent card: http://{host}:{port}/.well-known/agent.json")
    logger.info(f"  - Restate services: http://{host}:{port}/restate/v1/")
    asyncio.run(hypercorn.asyncio.serve(app, conf))


def run_pure_a2a_mode(hybrid_agent: HybridReimbursementAgent, host: str, port: int):
    """Run using pure A2A SDK (no Restate durability)."""
    import uvicorn

    # Get pure A2A application
    a2a_app = hybrid_agent.get_pure_a2a_app(host, port)

    logger.info(f"Pure A2A mode server running at http://{host}:{port}")
    logger.info("Note: This mode does not include Restate durability features")
    logger.info("Available endpoints:")
    logger.info(f"  - Agent card: http://{host}:{port}/.well-known/agent.json")
    logger.info(f"  - A2A endpoints: http://{host}:{port}/")

    uvicorn.run(a2a_app.build(), host=host, port=port)


if __name__ == '__main__':
    main()