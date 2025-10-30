# pylint: disable=C0116
"""Main entry point for reimbursement agent."""

import logging
import os
from fastapi import FastAPI
from dotenv import load_dotenv

from a2a_samples.reimbursement.agent import ReimbursementAgent, reimbursement_service
from a2a_samples.common.a2a.a2a_middleware import RestateA2AMiddleware
from a2a.types import AgentCard, AgentCapabilities, AgentSkill
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(process)d] [%(levelname)s] - %(message)s",
)
logger = logging.getLogger(__name__)


if __name__ == '__main__':
    """Run the reimbursement agent."""
    import restate
    import asyncio
    import hypercorn.asyncio

    try:
        # Check for required API keys
        if not os.getenv('OPENAI_API_KEY') and not os.getenv('GEMINI_API_KEY'):
            if not os.getenv('GOOGLE_GENAI_USE_VERTEXAI') == 'TRUE':
                raise Exception(
                    'Either OPENAI_API_KEY or GEMINI_API_KEY must be set, '
                    'or GOOGLE_GENAI_USE_VERTEXAI must be TRUE.'
                )

        # Define the agent card for A2A protocol
        agent_card = AgentCard(
            name="ReimbursementAgent",
            description="Advanced reimbursement agent with Google ADK intelligence and Restate durability",
            url=os.getenv("RESTATE_HOST", "http://localhost:8080"),
            version="1.0.0",
            capabilities=AgentCapabilities(
                streaming=False,
                push_notifications=False,
                state_transition_history=True,
            ),
            skills=[
                AgentSkill(
                    id="process_reimbursement",
                    name="Process Reimbursement",
                    description="Handle employee reimbursement requests with workflow management",
                    tags=["reimbursement", "finance", "workflow"],
                    examples=[
                        "Can you reimburse me $50 for client lunch on Dec 1st?",
                        "I need to submit a reimbursement for travel expenses",
                        "Process my $200 conference registration fee reimbursement",
                    ],
                ),
                AgentSkill(
                    id="form_management",
                    name="Form Management",
                    description="Create and manage reimbursement forms with validation",
                    tags=["forms", "validation", "data"],
                    examples=[
                        "Create a new reimbursement form",
                        "Validate submitted expense data",
                    ],
                ),
                AgentSkill(
                    id="approval_workflow",
                    name="Approval Workflow",
                    description="Handle approval workflows for large expenses",
                    tags=["approval", "workflow", "management"],
                    examples=[
                        "Route expense for manager approval",
                        "Check approval status",
                    ],
                ),
            ],
            default_input_modes=['text', 'text/plain'],
            default_output_modes=['text', 'text/plain'],
        )

        # Get hybrid middleware
        middleware = RestateA2AMiddleware(agent_card, ReimbursementAgent())

        app = FastAPI()

        @app.get("/.well-known/agent.json")
        async def agent_json():
            """Serve the agent card in A2A SDK format"""
            return agent_card

        # Mount both A2A SDK endpoints and Restate endpoints
        app.mount("/restate/v1", restate.app([*middleware, reimbursement_service]))

        conf = hypercorn.Config()
        host = "localhost"
        port = 9083
        conf.bind = [f"{host}:{port}"]
        logger.info(f"Server running at http://{host}:{port}")
        logger.info("Available endpoints:")
        logger.info(f"  - Agent card: http://{host}:{port}/.well-known/agent.json")
        logger.info(f"  - Restate services: http://{host}:{port}/restate/v1/")
        asyncio.run(hypercorn.asyncio.serve(app, conf))

    except Exception as e:
        logger.error(f'An error occurred during server startup: {e}')
        exit(1)
