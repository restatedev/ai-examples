import restate

from typing import Optional, Any
from google.adk.agents import BaseAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.plugins import BasePlugin
from google.adk.tools import BaseTool, ToolContext
from google.genai import types

from middleware.middleware import is_restate_agent, set_context, unset_context, wrap_with_restate


class RestatePlugin(BasePlugin):
    """A plugin to integrate Restate with the ADK framework."""

    def __init__(self, ctx: restate.ObjectContext | restate.Context):
        self.ctx = ctx
        super().__init__(name="restate_plugin")

    async def before_agent_callback(
            self, *, agent: BaseAgent, callback_context: CallbackContext
    ) -> Optional[types.Content]:
        if not is_restate_agent(agent):
            await wrap_with_restate(agent, self.ctx)
        set_context(agent, self.ctx)
        return None

    async def after_agent_callback(self, *, agent: BaseAgent, callback_context: CallbackContext) -> Optional[
        types.Content]:
        unset_context(agent)
        # TODO: consider unwrapping the agent to restore original model and tools
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