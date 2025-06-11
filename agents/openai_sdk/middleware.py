import restate
import json
import typing

from restate.serde import Serde
from openai.types.responses import (
    ResponseOutputMessage,
    ResponseOutputText,
    ResponseOutputRefusal,
    ResponseFunctionToolCall,
    ResponseComputerToolCall,
    ResponseFileSearchToolCall,
    ResponseFunctionWebSearch
)
from agents import (
    Usage,
    ModelResponse,
    Model,
    ModelSettings,
    Tool,
    TResponseInputItem,
    AsyncOpenAI,
    Handoff,
    ModelTracing,
    AgentOutputSchemaBase,
    OpenAIChatCompletionsModel
)
from agents.items import TResponseStreamEvent
from typing import AsyncIterator

class ModelResponseSerde(Serde[bytes]):
    def deserialize(self, buf: bytes) -> ModelResponse:
        """
        Deserializes bytes into a ModelResponse object.

        Args:
            data: The dictionary containing serialized ModelResponse data

        Returns:
            A ModelResponse object
        """

        data = json.loads(buf)
        output_items = []
        for item_dict in data["output"]:
            if item_dict.get("type") == "message":
                # Process content for message items
                content_list = []
                for content_item in item_dict.get("content", []):
                    if content_item.get("type") == "output_text":
                        content_list.append(ResponseOutputText(type="output_text", text=content_item["text"], annotations=content_item.get("annotations")))
                    elif content_item.get("type") == "refusal":
                        content_list.append(ResponseOutputRefusal(type="refusal", refusal=content_item["refusal"]))

                output_items.append(ResponseOutputMessage(
                    id=item_dict.get("id"),
                    type="message",
                    role=item_dict.get("role", "assistant"),
                    content=content_list,
                    status=item_dict.get("status")
                ))
            elif item_dict.get("type") == "function_call":
                output_items.append(ResponseFunctionToolCall(**item_dict))
            elif item_dict.get("type") == "computer_call":
                output_items.append(ResponseComputerToolCall(**item_dict))
            elif item_dict.get("type") == "file_search_call":
                output_items.append(ResponseFileSearchToolCall(**item_dict))
            elif item_dict.get("type") == "web_search_call":
                output_items.append(ResponseFunctionWebSearch(**item_dict))

        # Create the Usage object
        usage_data = data.get("usage", {})
        usage = Usage(
            input_tokens=usage_data.get("input_tokens", 0),
            output_tokens=usage_data.get("output_tokens", 0),
            total_tokens=usage_data.get("total_tokens", 0)
        )

        # Create and return the ModelResponse
        return ModelResponse(
            output=output_items,
            usage=usage,
            response_id=data.get("response_id")
        )

    def serialize(self, obj: typing.Optional[ModelResponse]) -> bytes:
        """
        Serializes a ModelResponse object to bytes

        Args:
            obj: The ModelResponse object to serialize

        Returns:
            Bytes containing the serialized ModelResponse object
        """
        if obj is None:
            return bytes()
        return json.dumps({
            "output": [output.model_dump(exclude_unset=True) for output in obj.output],
            "usage": {
                "input_tokens": obj.usage.input_tokens,
                "output_tokens": obj.usage.output_tokens,
                "total_tokens": obj.usage.total_tokens
            },
            "response_id": obj.response_id
        }).encode('utf-8')

class RestateModelWrapper(Model):
    def __init__(self, ctx: restate.Context):
        self.ctx = ctx
        self.name = f"RestateModelWrapper"

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
        model = OpenAIChatCompletionsModel(
            model="gpt-4o",
            openai_client=AsyncOpenAI()
        )
        return await self.ctx.run("call LLM", model.get_response, args=(
                system_instructions,
                input,
                model_settings,
                tools,
                output_schema,
                handoffs,
                tracing,
                previous_response_id,
            ), serde=ModelResponseSerde())

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
        """Stream a response from the model.

        Args:
            system_instructions: The system instructions to use.
            input: The input items to the model, in OpenAI Responses format.
            model_settings: The model settings to use.
            tools: The tools available to the model.
            output_schema: The output schema to use.
            handoffs: The handoffs available to the model.
            tracing: Tracing configuration.
            previous_response_id: the ID of the previous response. Generally not used by the model,
                except for the OpenAI Responses API.

        Returns:
            An iterator of response stream events, in OpenAI Responses format.
        """
        raise restate.TerminalError("Streaming is not supported in Restate. Use `get_response` instead.")
