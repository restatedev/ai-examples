import hypercorn
import asyncio
import restate

from app.mcp import agent_service as mcp_agent
from app.mcp_with_approval import agent_service as mcp_with_approval_agent
from app.websearch import agent_service as websearch_agent
from app.rollback_agent import agent_service as rollback_agent
from app.notify_when_ready import agent_service as notification_agent

app = restate.app(
    services=[mcp_agent, mcp_with_approval_agent, websearch_agent, rollback_agent, notification_agent]
)


def main():
    """Entry point for running the app."""
    conf = hypercorn.Config()
    conf.bind = ["0.0.0.0:9080"]
    asyncio.run(hypercorn.asyncio.serve(app, conf))


if __name__ == "__main__":
    main()
