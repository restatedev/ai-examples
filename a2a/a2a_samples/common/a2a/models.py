from abc import ABC, abstractmethod
import restate
from a2a.types import Part
from pydantic import BaseModel

class A2AAgent(ABC):
    """Agent interface that works with A2A SDK types."""

    @abstractmethod
    async def invoke(
        self, ctx: restate.ObjectContext, query: str, session_id: str
    ) -> "AgentInvokeResult":
        """Invoke the agent with a query."""
        pass


class AgentInvokeResult(BaseModel):
    """Result of agent invocation using A2A SDK types."""
    parts: list[Part]
    require_user_input: bool = False
    is_task_complete: bool = True