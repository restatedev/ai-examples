import hypercorn
import asyncio
import restate

from a_chaining.chaining import call_chaining_svc
from b_parallelization.parallelization import parallelization_svc
from c_routing.routing import routing_svc
from d_orchestrator_workers.orchestrator_workers import flexible_orchestrator
from e_evaluator_optimizer.evaluator_optimizer import evaluator_optimizer
from f_human_evaluator_optimizer.human_evaluator_optimizer import human_evaluator_optimizer

app = restate.app(
    services=[
        call_chaining_svc,
        parallelization_svc,
        routing_svc,
        flexible_orchestrator,
        evaluator_optimizer,
        human_evaluator_optimizer,
    ]
)

if __name__ == "__main__":
    conf = hypercorn.Config()
    conf.bind = ["0.0.0.0:9081"]
    asyncio.run(hypercorn.asyncio.serve(app, conf))
