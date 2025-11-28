import hypercorn
import asyncio
import restate

# Import all tour agents
from app.chat import chat
from app.durable_agent import agent_service as weather_agent
from app.sub_workflow_agent import (
    agent_service as sub_workflow_claim_approval_agent,
    human_approval_workflow,
)
from app.multi_agent import agent_service as multi_agent_claim_approval
from app.multi_agent_remote import agent_service as remote_multi_agent_claim_approval
from app.human_approval_agent import agent_service as human_claim_approval_agent
from app.human_approval_agent_with_timeout import (
    agent_service as human_claim_approval_with_timeouts_agent,
)
from app.advanced.rollback_agent import agent_service as booking_with_rollback_agent
from app.advanced.manual_loop_agent import manual_loop_agent
from app.advanced.mcp import chat as mcp_chat
from app.advanced.mcp_with_approval import chat as mcp_with_approvals_chat
from app.advanced.websearch import chat as websearch_chat

from app.parallel_agents import agent_service as parallel_agent_claim_approval
from app.parallel_tools_agent import agent_service as parallel_tool_claim_agent
from app.utils.utils import (
    fraud_agent_service,
    rate_comparison_agent_service,
    eligibility_agent_service,
)

# Create Restate app with all tour services
app = restate.app(
    services=[
        # Chat agents
        chat,
        # Durable execution
        weather_agent,
        # Orchestration
        multi_agent_claim_approval,
        remote_multi_agent_claim_approval,
        sub_workflow_claim_approval_agent,
        human_approval_workflow,
        # Human-in-the-loop
        human_claim_approval_agent,
        human_claim_approval_with_timeouts_agent,
        # Advanced patterns
        booking_with_rollback_agent,
        manual_loop_agent,
        mcp_chat,
        mcp_with_approvals_chat,
        websearch_chat,
        # Error handling
        # Parallel processing
        parallel_agent_claim_approval,
        parallel_tool_claim_agent,
        # Utils
        fraud_agent_service,
        eligibility_agent_service,
        rate_comparison_agent_service,
    ]
)


def main():
    """Entry point for running the app."""
    conf = hypercorn.Config()
    conf.bind = ["0.0.0.0:9080"]
    asyncio.run(hypercorn.asyncio.serve(app, conf))


if __name__ == "__main__":
    main()
