from abc import ABC, abstractmethod
from typing import Any

import restate
from pydantic import BaseModel


class A2AAgent(ABC):
    """Agent invoked inside a durable Restate handler."""

    @abstractmethod
    async def invoke(
        self, ctx: restate.ObjectContext, query: str, session_id: str
    ) -> "AgentInvokeResult":
        """Invoke the agent with a query."""
        pass


class AgentInvokeResult(BaseModel):
    """Agent result containing A2A 1.x ProtoJSON parts, e.g. {\"text\": \"hi\"}.

    JSON keeps this result serializable across Restate calls. The middleware
    converts parts to the SDK's protobuf types at the A2A boundary.
    """

    parts: list[dict[str, Any]]
    require_user_input: bool = False
    is_task_complete: bool = True
