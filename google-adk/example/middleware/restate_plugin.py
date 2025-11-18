import asyncio
from typing import Optional, Any

import restate
from google.adk.agents import InvocationContext
from google.adk.agents.callback_context import CallbackContext
from google.adk.events import Event
from google.adk.models import LlmRequest, LlmResponse, LLMRegistry
from google.adk.plugins import BasePlugin
from google.adk.tools import BaseTool, ToolContext


class RestatePlugin(BasePlugin):
    """A plugin to integrate Restate with the ADK framework."""

    def __init__(self, ctx: restate.ObjectContext):
        self._lock = asyncio.Lock()
        self.ctx = ctx
        super().__init__(name="restate_plugin")

    async def on_event_callback(
        self, *, invocation_context: InvocationContext, event: Event
    ) -> Optional[Event]:
        # TODO do check non-deterministic events by ignoring ID and timestamp fields
        return await self.ctx.run_typed(
            "persist event", lambda: event, restate.RunOptions(type_hint=Event)
        )

    async def before_model_callback(
        self, *, callback_context: CallbackContext, llm_request: LlmRequest
    ) -> Optional[LlmResponse]:

        model = LLMRegistry.new_llm(llm_request.model)

        async def call_llm() -> LlmResponse:
            # Without streaming the generator will yield only one response
            a_gen = model.generate_content_async(llm_request, stream=False)
            return await anext(a_gen)

        return await self.ctx.run_typed(
            "call LLM", call_llm, restate.RunOptions(max_attempts=3)
        )

    async def before_tool_callback(
        self,
        *,
        tool: BaseTool,
        tool_args: dict[str, Any],
        tool_context: ToolContext,
    ) -> Optional[dict]:
        # TODO how does this work for built-in tools that may not go through this path?
        tool_context.session.state["restate_context"] = self.ctx
        async with self._lock:
            result = await tool.run_async(args=tool_args, tool_context=tool_context)
            return result
