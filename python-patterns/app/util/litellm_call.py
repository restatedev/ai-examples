import typing
import litellm

from litellm.types.utils import Message, ModelResponse, Choices


async def llm_call(
    messages: str | list[dict[str, str]], tools: list | None = None
) -> Message:
    """
    Calls the model with the given prompt and returns the response.

    Args:
        messages (str): The user prompt to send to the model.
        tools (list, optional): List of tools for the model to use. Defaults to None.

    Returns:
        str: The response from the language model.
    """
    if tools is None:
        tools = []
    if isinstance(messages, str):
        messages = [{"role": "user", "content": messages}]
    resp = await litellm.acompletion(
        model="gpt-4o", messages=messages, tools=tools, stream=False
    )
    response = typing.cast(ModelResponse, resp)

    # Handle the response properly - litellm returns a ModelResponse object
    if hasattr(response, "choices") and response.choices:
        first_choice = typing.cast(Choices, response.choices[0])
        if hasattr(first_choice, "message") and first_choice.message:
            return first_choice.message

    raise RuntimeError("No content in response")
