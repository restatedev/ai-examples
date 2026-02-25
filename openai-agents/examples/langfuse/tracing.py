"""Custom tracing processor that flattens OpenAI agent spans so they all
appear as direct children of the Restate trace parent."""

from datetime import datetime
from typing import Any

from agents.tracing import Span, Trace
from opentelemetry import context as otel_context
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from restate.server_context import current_context, get_extension_data, set_extension_data, clear_extension_data

from openinference.instrumentation.openai_agents._processor import (
    OpenInferenceTracingProcessor,
    _get_span_name,
    _get_span_kind,
    _as_utc_nano,
    OPENINFERENCE_SPAN_KIND,
    LLM_SYSTEM,
)
from openinference.semconv.trace import OpenInferenceLLMSystemValues
import logging

logger = logging.getLogger(__name__)

_propagator = TraceContextTextMapPropagator()


_EXTENSION_KEY = "otel_trace_cleanup"


class _SpanCleanup:
    """Stored as Restate extension data. __close__ is called automatically
    when the Restate invocation context is cleaned up, ending any spans
    that were never properly closed (e.g. due to a failed invocation)."""

    def __init__(self, processor: 'RestateTracingProcessor', token):
        self._processor = processor
        self._token = token
        self._span_ids: list[str] = []

    def track_span(self, span_id: str):
        self._span_ids.append(span_id)

    def __close__(self):
        for span_id in self._span_ids:
            if otel_span := self._processor._otel_spans.pop(span_id, None):
                otel_span.end()
        if self._token is not None:
            otel_context.detach(self._token)
            self._token = None


class RestateTracingProcessor(OpenInferenceTracingProcessor):
    """All spans become direct children of the Restate trace parent,
    instead of being nested inside an agent workflow hierarchy."""

    def on_trace_start(self, trace: Trace) -> None:
        # Extract the W3C traceparent from Restate's attempt headers
        # and make it the active OTel context so all spans are parented
        # under the Restate invocation trace.
        ctx = current_context()
        if ctx is None:
            raise RuntimeError(
                "No Restate context found, only use the FlatTracingProcessor from within a Restate handler."
            )
        parent = _propagator.extract(ctx.request().attempt_headers)
        token = otel_context.attach(parent)
        set_extension_data(ctx, _EXTENSION_KEY, _SpanCleanup(self, token))

    def on_trace_end(self, trace: Trace) -> None:
        ctx = current_context()
        if ctx is None:
            raise RuntimeError(
                "No Restate context found, only use the FlatTracingProcessor from within a Restate handler."
            )

        cleanup = get_extension_data(ctx, _EXTENSION_KEY)
        if cleanup is not None:
            cleanup.__close__()
            clear_extension_data(ctx, _EXTENSION_KEY)

    def on_span_start(self, span: Span[Any]) -> None:
        if not span.started_at:
            return
        start_time = datetime.fromisoformat(span.started_at)
        span_name = _get_span_name(span)
        # context=None → uses the current OTel context (the Restate trace parent).
        otel_span = self._tracer.start_span(
            name=span_name,
            start_time=_as_utc_nano(start_time),
            attributes={
                OPENINFERENCE_SPAN_KIND: _get_span_kind(span.span_data),
                LLM_SYSTEM: OpenInferenceLLMSystemValues.OPENAI.value,
            },
        )
        self._otel_spans[span.span_id] = otel_span

        # Track this span for cleanup if the invocation fails before on_span_end fires
        ctx = current_context()
        if ctx is None:
            raise RuntimeError(
                "No Restate context found, only use the FlatTracingProcessor from within a Restate handler."
            )

        cleanup = get_extension_data(ctx, _EXTENSION_KEY)
        if cleanup is not None:
            cleanup.track_span(span.span_id)
