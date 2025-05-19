import os

import restate
import httpx

from pydantic import BaseModel
from restate.serde import PydanticJsonSerde

from common.types import AgentCard
from common.server.agent_session import (
    Agent,
    AgentInput,
    AgentResponse,
    run_agent_session,
)


class AgentList(BaseModel):
    agents: list[Agent] = []


host_agent_definition = Agent(
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
)


# Keyed by user id
host_agent_object = restate.VirtualObject("HostAgent")


@host_agent_object.handler()
async def handle_message(ctx: restate.ObjectContext, message: str) -> str:
    """Handle a message from the user."""
    agents_list = await ctx.get("agents", type_hint=AgentList) or AgentList()
    agents = agents_list.agents
    host_agent = host_agent_definition
    host_agent.handoffs = [remote_agent.name for remote_agent in agents]

    agent_input = AgentInput(
        starting_agent=host_agent, agents=[host_agent, *agents], message=message
    )
    agent_response = await run_agent_session(ctx, agent_input)
    return agent_response.final_output


@host_agent_object.handler(output_serde=PydanticJsonSerde(AgentList))
async def register_remote_agents(
    ctx: restate.ObjectContext, remote_agent_urls: list[str]
) -> AgentList:
    """Register a remote agent."""
    agents = await ctx.get("agents", type_hint=AgentList) or AgentList()

    remote_agents = []
    for remote_agent_url in remote_agent_urls:
        resp = httpx.get(f"{remote_agent_url}/.well-known/agent.json")
        resp.raise_for_status()
        agent_card = AgentCard(**resp.json())

        # Check if the agent with this name is already registered; and if so, remove it
        for i, agent in enumerate(agents.agents):
            if agent.name == agent_card.name:
                agents.agents.pop(i)
                break

        # Register the remote agent
        remote_agents.append(
            Agent(
                name=agent_card.name,
                handoff_description=agent_card.description,
                remote_url=agent_card.url,
            )
        )

    agents.agents.extend(remote_agents)
    ctx.set("agents", agents)
    return agents
