# pylint: disable=C0116
"""Hybrid reimbursement agent using Google ADK + Restate."""

import logging
import os
from typing import Any, Dict

from a2a_samples.common.a2a.adk_restate_bridge import ADKAgentFactory, RestateADKBridge
from a2a_samples.common.a2a.models import AgentCard, AgentSkill, AgentCapabilities

logger = logging.getLogger(__name__)


def create_hybrid_reimbursement_agent() -> RestateADKBridge:
    """Create a hybrid reimbursement agent that combines ADK and Restate."""

    # Create the ADK agent with Restate integration
    adk_agent = ADKAgentFactory.create_reimbursement_agent()

    # Define the agent card for A2A protocol
    agent_card = AgentCard(
        name="HybridReimbursementAgent",
        description="Advanced reimbursement agent with Google ADK intelligence and Restate durability",
        url=os.getenv("RESTATE_HOST", "http://localhost:8080"),
        version="1.0.0",
        capabilities=AgentCapabilities(
            streaming=False,
            pushNotifications=False,
            stateTransitionHistory=True,  # Enabled by Restate
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
    )

    # Create the bridge
    return RestateADKBridge(adk_agent, agent_card)


class HybridReimbursementAgent:
    """Wrapper class for easy instantiation of hybrid reimbursement agent."""

    def __init__(self):
        self.bridge = create_hybrid_reimbursement_agent()
        self.agent_card = self.bridge.agent_card
        self.adk_agent = self.bridge.adk_agent

    def get_traditional_middleware(self):
        """Get traditional Restate A2A middleware (full durability, custom protocol)."""
        return self.bridge.get_a2a_middleware()

    def get_hybrid_middleware(self):
        """Get hybrid middleware (A2A SDK protocol + Restate durability)."""
        return self.bridge.get_hybrid_middleware()

    def get_pure_a2a_app(self, host: str = "localhost", port: int = 8080):
        """Get pure A2A SDK application (standard protocol, no Restate durability)."""
        return self.bridge.get_pure_a2a_application(host, port)

    @property
    def supported_content_types(self):
        """Supported content types for the agent."""
        return ['text', 'text/plain']

    def get_processing_message(self) -> str:
        """Get processing message for the agent."""
        return 'Processing reimbursement request with hybrid ADK+Restate system...'