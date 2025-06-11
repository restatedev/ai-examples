import restate

from agents import (
    ModelResponse,
    Model,
    ModelSettings,
    Tool,
    TResponseInputItem,
    Handoff,
    ModelTracing,
    AgentOutputSchemaBase,
)
from agents.models.multi_provider import MultiProvider
from agents.items import TResponseStreamEvent
from typing import AsyncIterator


class RestateModelProvider(MultiProvider):
    def __init__(self, ctx: restate.Context):
        super().__init__()
        self.ctx = ctx

    def get_model(self, model_name: str | None) -> Model:
        return RestateModelWrapper(
            self.ctx, super().get_model(model_name or None)
        ).model


class RestateModelWrapper(Model):
    def __init__(self, ctx: restate.Context, model: Model):
        self.ctx = ctx
        self.model = model
        self.model_name = f"RestateModelWrapper"

    async def get_response(
        self,
        system_instructions: str | None,
        input: str | list[TResponseInputItem],
        model_settings: ModelSettings,
        tools: list[Tool],
        output_schema: AgentOutputSchemaBase | None,
        handoffs: list[Handoff],
        tracing: ModelTracing,
        previous_response_id: str | None,
    ) -> ModelResponse:
        return await self.ctx.run(
            "call LLM",
            self.model.get_response,
            args=(
                system_instructions,
                input,
                model_settings,
                tools,
                output_schema,
                handoffs,
                tracing,
                previous_response_id,
            ),
        )

    def stream_response(
        self,
        system_instructions: str | None,
        input: str | list[TResponseInputItem],
        model_settings: ModelSettings,
        tools: list[Tool],
        output_schema: AgentOutputSchemaBase | None,
        handoffs: list[Handoff],
        tracing: ModelTracing,
        *,
        previous_response_id: str | None,
    ) -> AsyncIterator[TResponseStreamEvent]:
        raise restate.TerminalError(
            "Streaming is not supported in Restate. Use `get_response` instead."
        )
