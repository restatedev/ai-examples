import hypercorn
import asyncio
import restate

from app.chaining import call_chaining_svc
from app.parallel_tools import parallel_tools_agent
from app.parallel_agents import parallelization_svc
from app.routing_to_agent import agent_router_service
from app.routing_to_tool import tool_router_service
from app.orchestrator_workers import orchestrator_svc
from app.evaluator_optimizer import evaluator_optimizer
from app.human_in_the_loop import content_moderator_svc
from app.chat import chat
from app.routing_to_remote_agent import (
    remote_agent_router_service,
    billing_agent_svc,
    product_agent_svc,
    account_agent_svc,
)

app = restate.app(
    services=[
        call_chaining_svc,
        parallelization_svc,
        parallel_tools_agent,
        agent_router_service,
        tool_router_service,
        orchestrator_svc,
        evaluator_optimizer,
        content_moderator_svc,
        chat,
        remote_agent_router_service,
        billing_agent_svc,
        account_agent_svc,
        product_agent_svc,
    ]
)

if __name__ == "__main__":
    conf = hypercorn.Config()
    conf.bind = ["0.0.0.0:9080"]
    asyncio.run(hypercorn.asyncio.serve(app, conf))
