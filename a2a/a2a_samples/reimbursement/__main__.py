import os
import restate
import logging
from fastapi import FastAPI

from a2a_samples.common.a2a.a2a_middleware import AgentMiddleware
from agent import reimbursement_agent, reimbursement_service, ReimbursementAgent
from a2a_samples.common.a2a.models import (
    MissingAPIKeyError,
    AgentCard,
    AgentSkill,
    AgentCapabilities,
)
from dotenv import load_dotenv


logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(process)d] [%(levelname)s] - %(message)s",
)
logger = logging.getLogger(__name__)

load_dotenv()

RESTATE_HOST = os.getenv("RESTATE_HOST", "http://localhost:8080")

AGENT_CARD = AgentCard(
    name=reimbursement_agent.name,
    description=reimbursement_agent.handoff_description,
    url=RESTATE_HOST,
    version="1.0.0",
    capabilities=AgentCapabilities(streaming=False),
    skills=[
        AgentSkill(
            id=tool.name,
            name=tool.name,
            description=tool.description,
            tags=["reimbursement"],
        )
        for tool in reimbursement_agent.tools
    ],
)

reimbursement_agent.remote_url = RESTATE_HOST
REIMBURSEMENT_AGENT = AgentMiddleware(
    AGENT_CARD,
    ReimbursementAgent(),
)

app = FastAPI()


@app.get("/.well-known/agent.json")
async def agent_json():
    """Serve the agent card"""
    return REIMBURSEMENT_AGENT.agent_card_json


app.mount("/restate/v1", restate.app([reimbursement_service, *REIMBURSEMENT_AGENT]))


def main():
    """Serve the agent at a specified port using hypercorn."""
    import asyncio
    import hypercorn.asyncio

    if not os.getenv("OPENAI_API_KEY"):
        raise MissingAPIKeyError("OPENAI_API_KEY environment variable not set.")

    port = os.getenv("AGENT_PORT", "9082")
    conf = hypercorn.Config()
    conf.bind = [f"0.0.0.0:{port}"]
    asyncio.run(hypercorn.asyncio.serve(app, conf))


if __name__ == "__main__":
    main()
