import os
import logging
import restate

from common.models import MissingAPIKeyError

from agent import host_agent_object
from dotenv import load_dotenv


load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

RESTATE_HOST = os.getenv("RESTATE_HOST", "http://localhost:8080")
AGENT_HOST = os.getenv("AGENT_HOST", "0.0.0.0:9080")


def main():
    """Serve the agent at a specified port using hypercorn."""
    import asyncio
    import hypercorn.asyncio

    if not os.getenv("OPENAI_API_KEY"):
        raise MissingAPIKeyError("OPENAI_API_KEY environment variable not set.")

    app = restate.app(services=[host_agent_object])

    conf = hypercorn.Config()
    conf.bind = [AGENT_HOST]
    asyncio.run(hypercorn.asyncio.serve(app, conf))


if __name__ == "__main__":
    main()
