import hypercorn
import asyncio
import restate

# Import all tour agents
from app.chat import chat
from app.durableexecution import weather_agent
from app.orchestration import (
    multi_agent_claim_approval,
    sub_workflow_claim_approval_agent,
    human_approval_workflow
)
from app.humanintheloop import (
    human_claim_approval_agent,
    human_claim_approval_with_timeouts_agent
)
from app.advanced import (
    booking_with_rollback_agent,
    manual_loop_agent
)
from app.errorhandling import (
    fail_on_terminal_error_agent,
    stop_on_terminal_error_agent
)
from app.parallelwork import (
    parallel_agent_claim_approval,
    parallel_tool_claim_agent
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
        sub_workflow_claim_approval_agent,
        human_approval_workflow,

        # Human-in-the-loop
        human_claim_approval_agent,
        human_claim_approval_with_timeouts_agent,

        # Advanced patterns
        booking_with_rollback_agent,
        manual_loop_agent,

        # Error handling
        fail_on_terminal_error_agent,
        stop_on_terminal_error_agent,

        # Parallel processing
        parallel_agent_claim_approval,
        parallel_tool_claim_agent,
    ]
)


def main():
    """Entry point for running the app."""
    conf = hypercorn.Config()
    conf.bind = ["0.0.0.0:9080"]
    asyncio.run(hypercorn.asyncio.serve(app, conf))


if __name__ == "__main__":
    main()
