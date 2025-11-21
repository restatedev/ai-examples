from typing import Optional, Any
import asyncio

from google.adk.agents import BaseAgent, LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.plugins import BasePlugin
from google.adk.tools import BaseTool, ToolContext
from google.genai import types
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.models import LLMRegistry
from google.adk.models.base_llm import BaseLlm

import restate

from middleware.restate_utils import current_restate_context


class RestatePlugin(BasePlugin):
    """A plugin to integrate Restate with the ADK framework."""

    _models: dict[str, BaseLlm]
    _locks: dict[str, asyncio.Lock]

    def __init__(self, *, max_model_call_retries: int = 3):
        super().__init__(name="restate_plugin")
        self._models = {}
        self._locks = {}
        self._max_model_call_retries = max_model_call_retries

    async def before_agent_callback(
        self, *, agent: BaseAgent, callback_context: CallbackContext
    ) -> Optional[types.Content]:
        if not isinstance(agent, LlmAgent):
            raise restate.TerminalError("RestatePlugin only supports LlmAgent agents.")
        ctx = current_restate_context()  # Ensure we have a Restate context
        if ctx is None:
            raise restate.TerminalError(
                """No Restate context found for RestatePlugin.
            Ensure that the agent is invoked within a restate handler and,
            using a ```with restate_overrides(ctx):``` block. around your agent use."""
            )
        model = (
            agent.model
            if isinstance(agent.model, BaseLlm)
            else LLMRegistry.new_llm(agent.model)
        )
        self._models[callback_context.invocation_id] = model
        self._locks[callback_context.invocation_id] = asyncio.Lock()

        id = callback_context.invocation_id
        event = ctx.request().attempt_finished_event

        async def release_task():
            """make sure to release resources when the agent finishes"""
            try:
                await event.wait()
            finally:
                self._models.pop(id, None)
                self._locks.pop(id, None)

        _ = asyncio.create_task(release_task())
        return None

    async def after_agent_callback(
        self, *, agent: BaseAgent, callback_context: CallbackContext
    ) -> Optional[types.Content]:
        self._models.pop(callback_context.invocation_id, None)
        self._locks.pop(callback_context.invocation_id, None)
        return None

    async def before_model_callback(
        self, *, callback_context: CallbackContext, llm_request: LlmRequest
    ) -> Optional[LlmResponse]:
        model = self._models[callback_context.invocation_id]
        ctx = current_restate_context()
        return await _generate_content_async(
            ctx, self._max_model_call_retries, model, llm_request
        )

    async def before_tool_callback(
        self,
        *,
        tool: BaseTool,
        tool_args: dict[str, Any],
        tool_context: ToolContext,
    ) -> Optional[dict]:
        tool_context.session.state["restate_context"] = current_restate_context()
        lock = self._locks[tool_context.invocation_id]
        await lock.acquire()
        # TODO: if we want we can also automatically wrap tools with ctx.run_typed here
        return None

    async def after_tool_callback(
        self,
        *,
        tool: BaseTool,
        tool_args: dict[str, Any],
        tool_context: ToolContext,
        result: dict,
    ) -> Optional[dict]:
        lock = self._locks[tool_context.invocation_id]
        lock.release()
        tool_context.session.state.pop("restate_context", None)
        return None

    async def on_tool_error_callback(
        self,
        *,
        tool: BaseTool,
        tool_args: dict[str, Any],
        tool_context: ToolContext,
        error: Exception,
    ) -> Optional[dict]:
        lock = self._locks[tool_context.invocation_id]
        lock.release()
        tool_context.session.state.pop("restate_context", None)
        return None

    async def close(self):
        self._models.clear()
        self._locks.clear()


async def _generate_content_async(
    ctx: restate.Context, max_attempts: int, model: BaseLlm, llm_request: LlmRequest
) -> LlmResponse:
    """Generate content using Restate's context."""

    async def call_llm() -> LlmResponse:
        a_gen = model.generate_content_async(llm_request, stream=False)
        try:
            result = await anext(a_gen)
            return result
        finally:
            await a_gen.aclose()

    return await ctx.run_typed(
        "call LLM", call_llm, restate.RunOptions(max_attempts=max_attempts)
    )
