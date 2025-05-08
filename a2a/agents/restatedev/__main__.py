from agent import chat_agents, reimbursement_agent
from common.types import AgentCard, AgentCapabilities, AgentSkill, MissingAPIKeyError
from agent import reimbursement_service
from common.server.a2a_server import a2a_services, GenericRestateAgent
import os
import logging
import hypercorn
import asyncio
import restate

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

RESTATE_HOST = os.getenv("RESTATE_HOST", "http://localhost:8080")
AGENT_HOST = os.getenv("AGENT_HOST", "0.0.0.0:9081")


def main():
    if not os.getenv("OPENAI_API_KEY"):
        raise MissingAPIKeyError("OPENAI_API_KEY environment variable not set.")

    reimbursement_agent.remote_url = (
        f"{RESTATE_HOST}/{reimbursement_agent.name}A2AServer/process_request"
    )
    services = a2a_services(
        agent_name=reimbursement_agent.name,
        agent_card=reimbursement_agent.as_agent_card(),
        agent=GenericRestateAgent(
            starting_agent=reimbursement_agent, agents=chat_agents
        ),
    )

    app = restate.app(services=[reimbursement_service, *services])

    conf = hypercorn.Config()
    conf.bind = [AGENT_HOST]
    asyncio.run(hypercorn.asyncio.serve(app, conf))


if __name__ == "__main__":
    main()
