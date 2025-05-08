from abc import ABC

import restate
from common.server.agent_session import AgentInput, run_agent_session, Agent
from common.types import AgentInvokeResult


class GenericRestateAgent(ABC):
    def __init__(self, starting_agent: Agent, agents: list[Agent]):
        super().__init__()
        self.starting_agent = starting_agent
        self.agents = agents

    async def invoke_with_context(
        self, ctx: restate.ObjectContext, query: str, session_id: str
    ) -> AgentInvokeResult:

        agent_input = AgentInput(
            starting_agent=self.starting_agent, agents=self.agents, message=query
        )

        agent_response = await run_agent_session(ctx, agent_input)
        result = agent_response.final_output

        parts = [{"type": "text", "text": result}]
        requires_input = "MISSING_INFO:" in result
        completed = not requires_input
        return AgentInvokeResult(
            parts=parts,
            require_user_input=requires_input,
            is_task_complete=completed,
        )
