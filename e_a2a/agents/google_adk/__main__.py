from agent import ReimbursementAgent
from common.types import MissingAPIKeyError, AgentCapabilities, AgentCard, AgentSkill
import restate
import os
import hypercorn
import asyncio
import logging
from dotenv import load_dotenv
from common.server.a2a_server import a2a_services

load_dotenv()

logger = logging.getLogger(__name__)

RESTATE_HOST = os.getenv("RESTATE_HOST", "http://localhost:8080")
AGENT_HOST = os.getenv("AGENT_HOST", "0.0.0.0:9082")


def main():
    try:
        if not os.getenv("GOOGLE_API_KEY"):
            raise MissingAPIKeyError("GOOGLE_API_KEY environment variable not set.")

        capabilities = AgentCapabilities(streaming=False)
        skill = AgentSkill(
            id="process_reimbursement",
            name="Process Reimbursement Tool",
            description="Helps with the reimbursement process for users given the amount and purpose of the reimbursement.",
            tags=["reimbursement"],
            examples=["Can you reimburse me $20 for my lunch with the clients?"],
        )
        agent_name = "ReimbursementAgent"
        agent_card = AgentCard(
            name=agent_name,
            description="This agent handles the reimbursement process for the employees given the amount and purpose of the reimbursement.",
            url=f"{RESTATE_HOST}/{agent_name}A2AServer/process_request",
            version="1.0.0",
            defaultInputModes=ReimbursementAgent.SUPPORTED_CONTENT_TYPES,
            defaultOutputModes=ReimbursementAgent.SUPPORTED_CONTENT_TYPES,
            capabilities=capabilities,
            skills=[skill],
        )
        services = a2a_services(
            agent_name=agent_name,
            agent_card=agent_card,
            agent=ReimbursementAgent(),
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
