import os
import restate

from fastapi import FastAPI

from agent import chat_agents, reimbursement_agent
from agent import reimbursement_service
from common.server.middleware import AgentMiddleware
from common.server.a2a_agent import GenericRestateAgent
from common.types import AgentCard, AgentCapabilities, AgentSkill, MissingAPIKeyError


RESTATE_HOST = os.getenv("RESTATE_HOST", "http://localhost:8080")
AGENT_HOST = os.getenv("AGENT_HOST", "0.0.0.0:9081")

reimbursement_agent.remote_url = RESTATE_HOST
REIMBURSEMENT_AGENT = AgentMiddleware(reimbursement_agent.as_agent_card(), GenericRestateAgent(
    starting_agent=reimbursement_agent, agents=chat_agents
))

app = FastAPI()


@app.get('/.well-known/agent.json')
async def agent_json():
    """Serve the agent card"""
    return REIMBURSEMENT_AGENT.agent_card_json


app.mount('/restate/v1', restate.app([reimbursement_service, *REIMBURSEMENT_AGENT]))


def main():
    """Serve the agent at a specified port using hypercorn."""
    import asyncio
    import hypercorn.asyncio

    if not os.getenv('GOOGLE_API_KEY'):
        raise MissingAPIKeyError('GOOGLE_API_KEY environment variable not set.')

    port = os.getenv('AGENT_PORT', '9081')
    conf = hypercorn.Config()
    conf.bind = [f'0.0.0.0:{port}']
    asyncio.run(hypercorn.asyncio.serve(app, conf))


if __name__ == '__main__':
    main()
