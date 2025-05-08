from common.server.agent_session import (
    Agent,
    AgentInput,
    AgentResponse,
    run_agent_session,
)

import restate

host_agent = Agent(
    name="HostAgent",
    handoff_description=(
        "This agent orchestrates the decomposition of the user request into"
        " tasks that can be performed by the child agents."
    ),
    instructions=f"""You are a expert delegator that can delegate the user request to the
    appropriate remote agents.
    
    For actionable tasks, you can hand off the task to remote agents to perform tasks.
    Be sure to include the remote agent name when you response to the user.
    To hand off to a remote agent, respond with the agent name in the following format. Never divert from this format:
    
    Please rely on tools to address the request, don't make up the response. If you are not sure, please ask the user for more details.
    Focus on the most recent parts of the conversation primarily.
    
    If there is an active agent, just forward the request to that agent as a handoff.
    """,
)


def get_agent_object(
    starting_agent: Agent, agents: list[Agent]
) -> restate.VirtualObject:
    host_agent = restate.VirtualObject("HostAgent")

    @host_agent.handler()
    async def handle_message(ctx: restate.ObjectContext, message: str) -> str:
        agent_input = AgentInput(
            starting_agent=starting_agent, agents=agents, message=message
        )
        agent_response = await run_agent_session(ctx, agent_input)
        return agent_response.final_output

    return host_agent
