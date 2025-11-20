from typing import AsyncGenerator, Callable
import asyncio
from functools import wraps

from google.adk.agents import BaseAgent
from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.models import LLMRegistry
from google.adk.agents.llm_agent import LlmAgent

from google.adk.agents.llm_agent import ToolUnion
from google.adk.tools.base_toolset import BaseToolset
from google.adk.tools.base_tool import BaseTool

import restate


class RestateModel(BaseLlm):
    """A simple model that restates the prompt."""

    __restate_context__: restate.Context | None = None
    __original_model__: BaseLlm

    async def generate_content_async(
            self, llm_request: "LlmRequest", stream: bool = False
    ) -> AsyncGenerator["LlmResponse", None]:
        if stream:
            raise restate.TerminalError(
                "Streaming is not supported in Restate. Set StreamingMode to NONE."
            )

        async def call_llm() -> LlmResponse:
            a_gen = self.__original_model__.generate_content_async(llm_request, stream=False)  # type: ignore
            try:
                result = await anext(a_gen)
                return result
            finally:
                await a_gen.aclose()

        ctx = self.__restate_context__
        assert ctx is not None, "Restate context is not set in the model."
        yield await ctx.run_typed(
            "call LLM", call_llm, restate.RunOptions(max_attempts=3)
        )


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


def is_restate_agent(agent: BaseAgent) -> bool:
    """Check if an agent is a RestateAgent."""
    return isinstance(agent, LlmAgent) and isinstance(agent.model, RestateModel)


async def wrap_with_restate(agent: BaseAgent, ctx: restate.Context):
    """Convert a BaseAgent to a RestateAgent."""
    if not isinstance(agent, LlmAgent):
        raise TypeError("Only LlmAgent can be converted to RestateAgent.")

    if isinstance(agent.model, str):
        agent.model = LLMRegistry.new_llm(agent.model)

    original_model = agent.model
    agent.model = RestateModel(**agent.model.__dict__)
    agent.model.__original_model__ = original_model

    agent.model.__restate_context__ = ctx
    agent.tools = await _as_sequential_tools(agent.tools)


def set_context(agent: BaseAgent, ctx: restate.Context):
    """Set the Restate context in the agent's model."""
    if isinstance(agent, LlmAgent) and isinstance(agent.model, RestateModel):
        agent.model.__restate_context__ = ctx


def unset_context(agent: BaseAgent):
    """Unset the Restate context from the agent's model."""
    if isinstance(agent, LlmAgent) and isinstance(agent.model, RestateModel):
        agent.model.__restate_context__ = None