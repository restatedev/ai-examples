import logging
import os
import restate
import httpx

from common.models import AgentCard
from common.agent_session import (
    Agent,
    AgentInput,
    run_agent,
)

logger = logging.getLogger(__name__)


def init_remote_agents():
    remote_agents = []
    for remote_agent_url in os.getenv("REMOTE_AGENTS", "").split(","):
        logger.info(f"Loading remote agent from {remote_agent_url}")
        resp = httpx.get(f"{remote_agent_url}/.well-known/agent.json")
        resp.raise_for_status()
        agent_card = AgentCard(**resp.json())
        remote_agents.append(
            Agent(
                name=agent_card.name,
                handoff_description=agent_card.description,
                remote_url=agent_card.url,
            )
        )
    return remote_agents


REMOTE_AGENTS = init_remote_agents()


host_agent = Agent(
    name="HostAgent",
    handoff_description=(
        "This agent orchestrates the decomposition of the user request into"
        " tasks that can be performed by the child agents."
    ),
    instructions=f"""You are a expert delegator that can delegate the user request to the
    appropriate remote agents.
    
    For actionable tasks, you can hand off the task to remote agents to perform tasks.
    If you have no remote agents available, you can ask the user to first register handoff agents.
    Be sure to include the remote agent name when you response to the user.
    To hand off to a remote agent, respond with the agent name in the following format. Never divert from this format:
    
    Please rely on tools to address the request, don't make up the response. If you are not sure, please ask the user for more details.
    Focus on the most recent parts of the conversation primarily.
    
    If there is an active agent, just forward the request to that agent as a handoff.
    """,
    handoffs=[remote_agent.name for remote_agent in REMOTE_AGENTS]
)

# Keyed by user id
host_agent_object = restate.VirtualObject("HostAgent")


@host_agent_object.handler()
async def handle_message(ctx: restate.ObjectContext, message: str) -> str:
    """Handle a message from the user."""
    agent_response = await run_agent(ctx, AgentInput(
        starting_agent=host_agent, agents=[host_agent, *REMOTE_AGENTS], message=message
    ))
    return agent_response.final_output