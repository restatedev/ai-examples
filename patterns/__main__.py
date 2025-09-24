import hypercorn
import asyncio
import restate

from app.chaining import call_chaining_svc
from app.parallelization import parallelization_svc
from app.routing_to_agent import agent_router_service
from app.routing_to_tool import tool_router_service
from app.orchestrator_workers import orchestrator_svc
from app.evaluator_optimizer import evaluator_optimizer
from app.human_in_the_loop import human_in_the_loop_svc
from app.routing_to_agent import billing_agent, product_agent, account_agent

app = restate.app(
    services=[
        call_chaining_svc,
        parallelization_svc,
        agent_router_service,
        tool_router_service,
        orchestrator_svc,
        evaluator_optimizer,
        human_in_the_loop_svc,
        billing_agent,
        account_agent,
        product_agent,
    ]
)

if __name__ == "__main__":
    conf = hypercorn.Config()
    conf.bind = ["0.0.0.0:9080"]
    asyncio.run(hypercorn.asyncio.serve(app, conf))
