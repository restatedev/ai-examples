import logging
import restate

from agents import Agent, Runner, RunConfig, ModelSettings

from a2a.common.openai.middleware import DurableModelCalls
from a2a.host_agent.utils import init_remote_agents

logger = logging.getLogger(__name__)


host_agent = Agent(
    name="HostAgent",
    handoff_description=(
        "This agent orchestrates the decomposition of the user request into"
        " tasks that can be performed by the child agents."
    ),
    instructions=f"""You are a expert delegator that can delegate the user request to the
    appropriate remote agents.
    
    For actionable tasks, you can hand off the task to remote agents to perform tasks.
    If you have no remote agents available, you can ask the user to first register agents.
    Be sure to include the remote agent name when you response to the user.
    To hand off to a remote agent, respond with the agent name in the following format. Never divert from this format:
    
    Please rely on tools to address the request, don't make up the response. If you are not sure, please ask the user for more details.
    Focus on the most recent parts of the conversation primarily.
    
    If there is an active agent, just forward the request to that agent as a handoff.
    """,
    tools=init_remote_agents(),
)

# Keyed by user id
host_agent_object = restate.VirtualObject("HostAgent")


@host_agent_object.handler()
async def handle_message(restate_context: restate.ObjectContext, message: str) -> str:
    """Handle a message from the user."""
    agent_response = await Runner.run(
        host_agent,
        input=message,
        context=restate_context,
        run_config=RunConfig(
            model_provider=DurableModelCalls(restate_context),
            model_settings=ModelSettings(parallel_tool_calls=False),
        ),
    )
    return agent_response.final_output
