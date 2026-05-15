import litellm
from litellm.types.utils import Message
from pydantic import BaseModel


async def llm_call(
    messages: list[dict[str, str]],
    prompt: str,
    tools: list | None = None,
    response_format: type[BaseModel] | None = None,
) -> Message:
    """
    Calls the model with the conversation history plus a new user prompt
    and returns the response.
    """
    if tools is None:
        tools = []
    response = await litellm.acompletion(
        model="gpt-5.2",
        messages=[*messages, {"role": "user", "content": prompt}],
        tools=tools,
        stream=False,
        response_format=response_format,
    )

    # Handle the response properly - litellm returns a ModelResponse object
    if len(response.choices) > 0:
        first_choice = response.choices[0]
        if first_choice.message is not None:
            return first_choice.message

    raise RuntimeError("No content in response")
