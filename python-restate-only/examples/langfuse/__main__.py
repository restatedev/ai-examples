# <start_here>
import litellm
from langfuse import get_client
from opentelemetry import trace as trace_api
from restate.ext.tracing import RestateTracerProvider
from litellm.integrations.langfuse.langfuse_otel import LangfuseOtelLogger

# Initialize Langfuse (sets up the global OTEL tracer provider + exporter)
langfuse = get_client()

# Create Restate-aware Langfuse OTEL logger for LiteLLM
litellm.callbacks = [
    LangfuseOtelLogger(
        tracer_provider=RestateTracerProvider(trace_api.get_tracer_provider())
    )
]

# <end_here>

if __name__ == "__main__":
    import hypercorn
    import asyncio
    import restate
    from agent import agent_service

    app = restate.app(services=[agent_service])

    conf = hypercorn.Config()
    conf.bind = ["0.0.0.0:9080"]
    asyncio.run(hypercorn.asyncio.serve(app, conf))
