import hypercorn
import asyncio
import restate

from langfuse import get_client
from opentelemetry import trace as trace_api
from openinference.instrumentation.google_adk import GoogleADKInstrumentor
from restate.ext.tracing import RestateTracerProvider

from agent import claim_service

# Initialize Langfuse (sets up the global OTEL tracer provider + exporter)
langfuse = get_client()

# Instrument Google ADK with Restate-aware tracing
GoogleADKInstrumentor().instrument(
    tracer_provider=RestateTracerProvider(trace_api.get_tracer_provider())
)


if __name__ == "__main__":
    app = restate.app(services=[claim_service])

    conf = hypercorn.Config()
    conf.bind = ["0.0.0.0:9080"]
    asyncio.run(hypercorn.asyncio.serve(app, conf))