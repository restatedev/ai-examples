import asyncio
import uuid
from typing import Optional, Any

import restate
from google.adk.agents import InvocationContext
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmRequest, LlmResponse, LLMRegistry
from google.adk.plugins import BasePlugin
from google.adk.tools import BaseTool, ToolContext
from google.genai import types


class RestatePlugin(BasePlugin):
    """A plugin to integrate Restate with the ADK framework."""

    def __init__(self, ctx: restate.ObjectContext):
        self._lock = asyncio.Lock()
        self.ctx = ctx
        super().__init__(name="restate_plugin")

    async def before_run_callback(
       self, *, invocation_context: InvocationContext
    ) -> Optional[types.Content]:
      # Patch uuid.uuid4 to use restate's uuid generator (pending better solution)
      def new_uuid():
          new_id = self.ctx.run_typed("uuid", lambda: str(uuid.uuid4()))
          return new_id

      uuid.uuid4 = new_uuid
      return None


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
        async with self._lock:
            result = await tool.run_async(args=tool_args, tool_context=tool_context)
            return result