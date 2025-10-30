from abc import ABC, abstractmethod
import restate
from a2a.types import Part

class A2AAgent(ABC):
    """Agent interface that works with A2A SDK types."""

    @abstractmethod
    async def invoke(
        self, ctx: restate.ObjectContext, query: str, session_id: str
    ) -> "AgentInvokeResult":
        """Invoke the agent with a query."""
        pass


class AgentInvokeResult:
    """Result of agent invocation using A2A SDK types."""

    def __init__(self, parts: list[Part], require_user_input: bool = False, is_task_complete: bool = True):
        self.parts = parts
        self.require_user_input = require_user_input
        self.is_task_complete = is_task_complete