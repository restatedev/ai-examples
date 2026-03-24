import hypercorn
import asyncio
import restate

from langfuse import get_client
from opentelemetry import trace as trace_api
from openinference.instrumentation import OITracer, TraceConfig
from agents import set_trace_processors

from utils.tracing import RestateTracingProcessor
from agent import claim_service
from evaluation import evaluation_service

# Initialize Langfuse (sets up the global OTEL tracer provider + exporter)
langfuse = get_client()
tracer = OITracer(
    trace_api.get_tracer("openinference.openai_agents"), config=TraceConfig()
)
set_trace_processors([RestateTracingProcessor(tracer)])

if __name__ == "__main__":
    app = restate.app(services=[claim_service, evaluation_service])

    conf = hypercorn.Config()
    conf.bind = ["0.0.0.0:9080"]
    asyncio.run(hypercorn.asyncio.serve(app, conf))
