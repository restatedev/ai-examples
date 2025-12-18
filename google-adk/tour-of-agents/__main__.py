import hypercorn
import asyncio
import restate

from app.chat import chat
from app.durable_agent import agent_service as weather_agent
from app.human_approval_agent import agent_service as human_claim_approval_agent
from app.human_approval_agent_with_timeout import (
    agent_service as human_claim_approval_with_timeout_agent,
)
from app.multi_agent import agent_service as multi_agent_claim_approval
from app.multi_agent_remote import agent_service as multi_agent_remote
from app.parallel_agents import agent_service as parallel_agent_claim_approval
from app.parallel_tools import agent_service as parallel_tool_claim_agent
from app.sub_workflow_agent import human_approval_workflow
from app.sub_workflow_agent import agent_service as sub_workflow_agent
from app.error_handling import agent_service as error_handling_agent
from app.utils.utils import (
    fraud_agent_service,
    rate_comparison_agent_service,
    eligibility_agent_service,
)

app = restate.app(
    services=[
        # Chat agents
        chat,
        # Durable execution
        weather_agent,
        # Orchestration
        multi_agent_claim_approval,
        multi_agent_remote,
        human_approval_workflow,
        sub_workflow_agent,
        # Human-in-the-loop
        human_claim_approval_agent,
        human_claim_approval_with_timeout_agent,
        # Parallel processing
        parallel_agent_claim_approval,
        parallel_tool_claim_agent,
        # Error handling
        error_handling_agent,
        # Utility agents
        fraud_agent_service,
        rate_comparison_agent_service,
        eligibility_agent_service,
    ]
)


def main():
    """Entry point for running the app."""
    conf = hypercorn.Config()
    conf.bind = ["0.0.0.0:9080"]
    asyncio.run(hypercorn.asyncio.serve(app, conf))


if __name__ == "__main__":
    main()
