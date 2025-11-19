import restate
import asyncio
from functools import wraps
from typing import Optional, Any, Callable

from google.adk.agents import BaseAgent, LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.llm_agent import ToolUnion
from google.adk.plugins import BasePlugin
from google.adk.tools import BaseTool, ToolContext
from google.adk.tools.base_toolset import BaseToolset
from google.genai import types

from middleware.middleware import durable_model_calls


class RestatePlugin(BasePlugin):
    """A plugin to integrate Restate with the ADK framework."""

    def __init__(self, ctx: restate.ObjectContext):
        self.ctx = ctx
        super().__init__(name="restate_plugin")

    async def before_agent_callback(
        self, *, agent: BaseAgent, callback_context: CallbackContext
    ) -> Optional[types.Content]:

        # Persist agent model calls in the Restate journal
        # This needs to be done here instead of in before_model_callback
        # because otherwise terminal errors lead to infinitely retried RuntimeErrors
        # because all errors in plugins are turned into RuntimeErrors by the ADK.
        agent.model = durable_model_calls(self.ctx, agent.model)

        # Wrap tools to be sequential within the same agent invocation
        # This needs to be done here instead of in before_tool_callback
        # because otherwise terminal errors lead to infinitely retried RuntimeErrors
        # because all errors in plugins are turned into RuntimeErrors by the ADK.
        if isinstance(agent, LlmAgent):
            agent.tools = await _as_sequential_tools(agent.tools)
        return None

    async def before_tool_callback(
        self,
        *,
        tool: BaseTool,
        tool_args: dict[str, Any],
        tool_context: ToolContext,
    ) -> Optional[dict]:
        # Make the Restate context available to tools via ToolContext
        tool_context.session.state["restate_context"] = self.ctx
        return None


async def _as_sequential_tools(tools: list[ToolUnion]) -> list[ToolUnion]:
    """
    Wrap ADK tools so that calls from the same agent invocation
    are sequential, but other agent invocations can run in parallel.
    """
    lock = asyncio.Lock()  # local to this invocation

    async def _sequential_base_tool(base_tool: BaseTool):
        base_tool_fn = base_tool.run_async

        @wraps(base_tool_fn)
        async def wrapper(*args, _tool_fn=base_tool_fn, **kwargs):
            async with lock:
                result = _tool_fn(*args, **kwargs)
                if asyncio.iscoroutine(result):
                    return await result
                return result

        base_tool.run_async = wrapper
        return base_tool

    wrapped_tools = []
    for tool_fn in tools:
        if isinstance(tool_fn, Callable):

            @wraps(tool_fn)
            async def wrapper(*args, _tool_fn=tool_fn, **kwargs):
                async with lock:
                    result = _tool_fn(*args, **kwargs)
                    if asyncio.iscoroutine(result):
                        return await result
                    return result

            wrapped_tools.append(wrapper)

        elif isinstance(tool_fn, BaseToolset):
            for tool in await tool_fn.get_tools():
                wrapped_tools.append(await _sequential_base_tool(tool))

        elif isinstance(tool_fn, BaseTool):
            wrapped_tools.append(await _sequential_base_tool(tool_fn))

    return wrapped_tools
