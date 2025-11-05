import hypercorn
import asyncio
import restate

from app.chat import chat
from app.durable_agent import agent_service as weather_agent
from app.human_approval_agent import agent_service as human_claim_approval_agent
from app.human_approval_agent_with_timeout import (
    agent_service as human_claim_approval_with_timeouts_agent,
)
from app.multi_agent import agent_service as multi_agent_claim_approval
from app.multi_agent_remote import agent_service as remote_multi_agent_claim_approval
from app.utils.utils import (
    fraud_agent_service,
    rate_comparison_agent_service,
    eligibility_agent_service,
)

app = restate.app(
    services=[
        chat,
        weather_agent,
        human_claim_approval_agent,
        human_claim_approval_with_timeouts_agent,
        multi_agent_claim_approval,
        remote_multi_agent_claim_approval,
        fraud_agent_service,
        rate_comparison_agent_service,
        eligibility_agent_service,
    ]
)


def main():
    """Entry point for running the app."""
    conf = hypercorn.Config()
    conf.bind = ["0.0.0.0:9081"]
    asyncio.run(hypercorn.asyncio.serve(app, conf))


if __name__ == "__main__":
    main()
