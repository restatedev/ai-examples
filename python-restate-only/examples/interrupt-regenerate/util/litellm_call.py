import litellm
from litellm.types.utils import Message
from pydantic import BaseModel


async def llm_call(
    messages: str | list[dict[str, str]],
    tools: list | None = None,
    response_format: type[BaseModel] | None = None,
) -> Message:
    """
    Calls the model with the given prompt and returns the response.

    Args:
        messages (str): The user prompt to send to the model.
        tools (list, optional): List of tools for the model to use. Defaults to None.

    Returns:
        Message: The response from the language model.
    """
    if tools is None:
        tools = []
    if isinstance(messages, str):
        messages = [{"role": "user", "content": messages}]
    response = await litellm.acompletion(
        model="gpt-5.2",
        messages=messages,
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
