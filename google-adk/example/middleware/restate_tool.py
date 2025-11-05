from typing import Any

import restate
from google.adk.models import LlmRequest
from google.adk.tools import BaseTool, ToolContext


class RestateTool(BaseTool):

    def __init__(self, ctx: restate.ObjectContext, tool: BaseTool):
        self.ctx = ctx
        self.tool = tool
        super().__init__(name=tool.name, description=tool.description)

    async def run_async(
            self, *, args: dict[str, Any], tool_context: ToolContext
    ) -> Any:
        """Runs the tool with the given arguments and context.

        NOTE:
          - Required if this tool needs to run at the client side.
          - Otherwise, can be skipped, e.g. for a built-in GoogleSearch tool for
            Gemini.

        Args:
          args: The LLM-filled arguments.
          tool_context: The context of the tool.

        Returns:
          The result of running the tool.
        """

        async def run_tool() -> Any:
            return await super().run_async(args=args, tool_context=tool_context)
        return await self.ctx.run_typed(
            super().name,
            run_tool
        )

    async def process_llm_request(
            self, *, tool_context: ToolContext, llm_request: LlmRequest
    ) -> None:
        """Processes the outgoing LLM request for this tool.

        Use cases:
        - Most common use case is adding this tool to the LLM request.
        - Some tools may just preprocess the LLM request before it's sent out.

        Args:
          tool_context: The context of the tool.
          llm_request: The outgoing LLM request, mutable this method.
        """
        async def process_request():
            return await self.tool.process_llm_request(tool_context=tool_context, llm_request=llm_request)
        return await self.ctx.run_typed(
            self.tool.name,
            process_request
        )


