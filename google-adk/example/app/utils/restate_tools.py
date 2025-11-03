import asyncio
from functools import wraps
from typing import Callable, Any


def restate_tools(*tools: Callable[..., Any]) -> list[Callable[..., Any]]:
    """
    Wrap ADK tools so that calls from the same agent invocation
    are sequential, but other agent invocations can run in parallel.
    """
    lock = asyncio.Lock()  # local to this invocation

    wrapped_tools = []

    for tool_fn in tools:
        # Wrap using functools.wraps to preserve signature for ADK
        @wraps(tool_fn)
        async def wrapper(*args, _tool_fn=tool_fn, **kwargs):
            async with lock:
                result = _tool_fn(*args, **kwargs)
                if asyncio.iscoroutine(result):
                    return await result
                return result

        wrapped_tools.append(wrapper)

    return wrapped_tools