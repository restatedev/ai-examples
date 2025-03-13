# ---------------------------------------------------------------------------
# Model response serializer
import json
import typing
from typing import Dict, Any

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
    ModelResponse
)


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
            referenceable_id=data.get("referenceable_id")
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
            "referenceable_id": obj.referenceable_id
        }).encode('utf-8')