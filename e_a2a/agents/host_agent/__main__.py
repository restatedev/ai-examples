import httpx

from common.server.agent_session import Agent
from common.types import AgentCard, MissingAPIKeyError
import os
import logging
import hypercorn
import asyncio
import restate

from agent import host_agent, get_agent_object

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

RESTATE_HOST = os.getenv("RESTATE_HOST", "http://localhost:8080")
AGENT_HOST = os.getenv("AGENT_HOST", "0.0.0.0:9080")
remote_agent_urls = [
    f"{RESTATE_HOST}/ReimbursementAgentA2AServer",
    f"{RESTATE_HOST}/CurrencyAgentA2AServer",
]


def main():
    try:
        if not os.getenv("OPENAI_API_KEY"):
            raise MissingAPIKeyError("OPENAI_API_KEY environment variable not set.")

        remote_agents = []
        for remote_agent_url in remote_agent_urls:
            resp = httpx.get(f"{remote_agent_url}/get_agent_card")
            resp.raise_for_status()
            agent_card = AgentCard(**resp.json())
            remote_agents.append(
                # TODO include tools etc?
                Agent(
                    name=agent_card.name,
                    handoff_description=agent_card.description,
                    remote_url=agent_card.url,
                )
            )
        host_agent.handoffs = [remote_agent.name for remote_agent in remote_agents]

        agent_object = get_agent_object(
            starting_agent=host_agent, agents=[host_agent, *remote_agents]
        )

        app = restate.app(services=[agent_object])

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
