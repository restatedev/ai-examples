# <start_here>
from langfuse import get_client
from opentelemetry import trace as trace_api
from openinference.instrumentation import OITracer, TraceConfig
from openinference.instrumentation.openai_agents._processor import (
    OpenInferenceTracingProcessor,
)
from agents import set_trace_processors
from restate.ext.tracing import RestateTracer

# Initialize Langfuse (sets up the global OTEL tracer provider + exporter)
langfuse = get_client()
tracer = OITracer(
    RestateTracer(trace_api.get_tracer("openinference.openai_agents")),
    config=TraceConfig(),
)
set_trace_processors([OpenInferenceTracingProcessor(tracer)])

# <end_here>

if __name__ == "__main__":
    import hypercorn
    import asyncio
    import restate
    from agent import claim_service
    from evaluation import evaluation_service

    app = restate.app(services=[claim_service, evaluation_service])

    conf = hypercorn.Config()
    conf.bind = ["0.0.0.0:9080"]
    asyncio.run(hypercorn.asyncio.serve(app, conf))
