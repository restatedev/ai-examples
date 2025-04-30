import hypercorn
import asyncio
import restate

from a_orchestrating_llm_calls.a_chaining.service import call_chaining_svc
from a_orchestrating_llm_calls.b_parallelization.service import parallelization_svc
from a_orchestrating_llm_calls.c_routing.service import routing_svc
from a_orchestrating_llm_calls.d_orchestrator_workers.service import flexible_orchestrator
from a_orchestrating_llm_calls.e_evaluator_optimizer.service import evaluator_optimizer
from a_orchestrating_llm_calls.f_human_evaluator_optimizer.service import human_evaluator_optimizer


def main():
    """Entry point for running the app."""
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
    
    conf = hypercorn.Config()
    conf.bind = ["0.0.0.0:9080"]
    asyncio.run(hypercorn.asyncio.serve(app, conf))

if __name__ == "__main__":
    main()
