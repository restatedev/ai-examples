from __future__ import annotations

from typing import Any
from typing import TYPE_CHECKING

from google.adk.tools import AgentTool
from google.genai import types
from typing_extensions import override

from google.adk.utils.context_utils import Aclosing
from google.adk.tools.tool_context import ToolContext

if TYPE_CHECKING:
    from google.adk.agents.base_agent import BaseAgent


# TODO This will be fixed on main very soon: https://github.com/google/adk-python/pull/2890
# Then this can be removed
class RestateAgentTool(AgentTool):
    """A tool that wraps an agent as a Restate Agent.

    This tool allows an agent to be called as a tool within a larger application.
    The agent's input schema is used to define the tool's input parameters, and
    the agent's output is returned as the tool's result.

    Attributes:
      agent: The agent to wrap.
      skip_summarization: Whether to skip summarization of the agent output.
    """

    def __init__(self, agent: BaseAgent, skip_summarization: bool = False):
        self.agent = agent
        self.skip_summarization: bool = skip_summarization

        super().__init__(agent=agent, skip_summarization=skip_summarization)

    @override
    async def run_async(
        self,
        *,
        args: dict[str, Any],
        tool_context: ToolContext,
    ) -> Any:
        from google.adk.agents.llm_agent import LlmAgent
        from google.adk.runners import Runner

        if self.skip_summarization:
            tool_context.actions.skip_summarization = True

        if isinstance(self.agent, LlmAgent) and self.agent.input_schema:
            input_value = self.agent.input_schema.model_validate(args)
            content = types.Content(
                role="user",
                parts=[
                    types.Part.from_text(
                        text=input_value.model_dump_json(exclude_none=True)
                    )
                ],
            )
        else:
            content = types.Content(
                role="user",
                parts=[types.Part.from_text(text=args["request"])],
            )
        invocation_context = tool_context._invocation_context
        parent_app_name = invocation_context.app_name if invocation_context else None
        child_app_name = parent_app_name or self.agent.name
        runner = Runner(
            app_name=child_app_name,
            agent=self.agent,
            session_service=tool_context._invocation_context.session_service,
            memory_service=tool_context._invocation_context.memory_service,
            credential_service=tool_context._invocation_context.credential_service,
            plugins=list(tool_context._invocation_context.plugin_manager.plugins),
        )

        state_dict = {
            k: v
            for k, v in tool_context.state.to_dict().items()
            if not k.startswith("_adk")  # Filter out adk internal states
        }
        session = await runner.session_service.create_session(
            app_name=child_app_name,
            user_id=tool_context._invocation_context.user_id,
            state=state_dict,
            session_id=tool_context.session.id,
        )

        last_content = None
        async with Aclosing(
            runner.run_async(
                user_id=session.user_id, session_id=session.id, new_message=content
            )
        ) as agen:
            async for event in agen:
                # Forward state delta to parent session.
                if event.actions.state_delta:
                    tool_context.state.update(event.actions.state_delta)
                if event.content:
                    last_content = event.content

        if not last_content:
            return ""
        merged_text = "\n".join(p.text for p in last_content.parts if p.text)
        if isinstance(self.agent, LlmAgent) and self.agent.output_schema:
            tool_result = self.agent.output_schema.model_validate_json(
                merged_text
            ).model_dump(exclude_none=True)
        else:
            tool_result = merged_text
        return tool_result
