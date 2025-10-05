import litellm
from typing import Optional, List

from litellm.types.utils import Message
from restate import TerminalError


def llm_call(
    prompt: str = None,
    system: str = None,
    messages: Optional[list[dict[str, str]]] = None,
    tools: Optional[List] = None,
) -> Message:
    """
    Calls the model with the given prompt and returns the response.

    Args:
        prompt (str): The user prompt to send to the model.
        system (str, optional): The system prompt to send to the model. Defaults to "".
        messages (list, optional): Previous messages for context in chat models. Defaults to None.
        tools (list, optional): List of tools for the model to use. Defaults to None.

    Returns:
        str: The response from the language model.
    """

    if not prompt and not messages:
        raise TerminalError("Either prompt or messages must be provided.")

    messages = messages or []
    if system:
        messages.append({"role": "system", "content": system})
    if prompt:
        messages.append({"role": "user", "content": prompt})
    content = (
        litellm.completion(model="gpt-4o", messages=messages, tools=tools)
        .choices[0]
        .message
    )

    if content:
        return content
    else:
        raise RuntimeError("No content in response")
