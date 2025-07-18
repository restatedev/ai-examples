import restate

from agents import (
    Usage,
    Model,
    ModelSettings,
    Tool,
    TResponseInputItem,
    Handoff,
    ModelTracing,
    AgentOutputSchemaBase,
    RunContextWrapper,
)
from agents.models.multi_provider import MultiProvider
from agents.items import TResponseStreamEvent, TResponseOutputItem
from typing import AsyncIterator

from restate._internal import VMException
from restate.exceptions import TerminalError
from pydantic import BaseModel
from agents import AgentsException


# This error type indicates that both the OpenAI agents and Restate should not retry.
class AgentTerminalError(TerminalError, AgentsException):
    """A terminal error that is also recognized as an OpenAI agents exception"""

    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message, status_code)
        # Initialize the OpenAI agents exception part if needed


# This error function should be used for all tools. To ensure terminal errors are not retried by agents.
def restate_tool_error_function(
    ctx: RunContextWrapper[restate.ObjectContext], error: Exception
) -> str:
    if isinstance(error, restate.TerminalError):
        # Propagate terminal errors
        raise AgentTerminalError(error.message, error.status_code)
    else:
        # Other errors will be fed into the agent
        return f"An error occurred while running the tool. Please try again. Error: {str(error)}"


# The OpenAI ModelResponse class is a dataclass with Pydantic fields.
# The Restate SDK cannot serialize this. So we turn the ModelResponse int a Pydantic model.
class RestateModelResponse(BaseModel):
    output: list[TResponseOutputItem]
    """A list of outputs (messages, tool calls, etc) generated by the model"""

    usage: Usage
    """The usage information for the response."""

    response_id: str | None
    """An ID for the response which can be used to refer to the response in subsequent calls to the
    model. Not supported by all model providers.
    If using OpenAI models via the Responses API, this is the `response_id` parameter, and it can
    be passed to `Runner.run`.
    """

    def to_input_items(self) -> list[TResponseInputItem]:
        return [it.model_dump(exclude_unset=True) for it in self.output]  # type: ignore


class DurableModelCalls(MultiProvider):
    """
    A Restate model provider that wraps the OpenAI SDK's default MultiProvider.
    """

    def __init__(self, ctx: restate.Context):
        super().__init__()
        self.ctx = ctx

    def get_model(self, model_name: str | None) -> Model:
        return RestateModelWrapper(self.ctx, super().get_model(model_name or None))


class RestateModelWrapper(Model):
    """
    A wrapper around the OpenAI SDK's Model that persists LLM calls in the Restate journal.
    """

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
    ) -> RestateModelResponse:
        async def call_llm() -> RestateModelResponse:
            resp = await self.model.get_response(
                system_instructions=system_instructions,
                input=input,
                model_settings=model_settings,
                tools=tools,
                output_schema=output_schema,
                handoffs=handoffs,
                tracing=tracing,
                previous_response_id=previous_response_id,
            )
            return RestateModelResponse(
                output=resp.output,
                usage=resp.usage,
                response_id=resp.response_id,
            )

        return await self.ctx.run("call LLM", call_llm, max_attempts=3)

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
