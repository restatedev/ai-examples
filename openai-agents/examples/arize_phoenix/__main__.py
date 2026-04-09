# <start_here>
from phoenix.otel import register
from opentelemetry import trace as trace_api
from openinference.instrumentation import OITracer, TraceConfig
from openinference.instrumentation.openai_agents._processor import (
    OpenInferenceTracingProcessor,
)
from agents import set_trace_processors
from restate.ext.tracing import RestateTracerProvider

# Initialize Arize Phoenix (sets up the global OTEL tracer provider + exporter).
register()
tracer = OITracer(
    RestateTracerProvider(trace_api.get_tracer_provider()).get_tracer(
        "openinference.openai_agents"
    ),
    config=TraceConfig(),
)
set_trace_processors([OpenInferenceTracingProcessor(tracer)])

# <end_here>

if __name__ == "__main__":
    import hypercorn
    import asyncio
    import restate
    from agent import claim_service

    app = restate.app(services=[claim_service])

    conf = hypercorn.Config()
    conf.bind = ["0.0.0.0:9080"]
    asyncio.run(hypercorn.asyncio.serve(app, conf))
