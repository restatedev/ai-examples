import hypercorn
import asyncio
import restate

from chaining.service import call_chaining_svc
from parallelization.service import parallelization_svc
from routing.service import routing_svc
from orchestrator_workers.service import flexible_orchestrator
from evaluator_optimizer.service import evaluator_optimizer
from human_evaluator_optimizer.service import human_evaluator_optimizer

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


def main():
    """Entry point for running the app."""
    conf = hypercorn.Config()
    conf.bind = ["0.0.0.0:9080"]
    asyncio.run(hypercorn.asyncio.serve(app, conf))


if __name__ == "__main__":
    main()
