import uuid

import restate
from typing import Optional, List, AsyncGenerator

from google.adk import Runner
from google.adk.agents import BaseAgent
from google.adk.events import Event
from google.adk.plugins import BasePlugin

from app.common.adk.restate_session_service import RestateSessionService


class RestateRunner(Runner):
    def __init__(
        self,
        *,
        restate_context: restate.ObjectContext,
        app_name: Optional[str] = None,
        agent: Optional[BaseAgent] = None,
        plugins: Optional[List[BasePlugin]] = None,
        session_service: RestateSessionService,
        # TODO support the other args
    ):
        """Initializes the RestateRunner."""
        self.ctx = restate_context
        super().__init__(
            app_name=app_name,
            agent=agent,
            plugins=plugins,
            session_service=session_service,
        )

    def run_async(self, *args, **kwargs) -> AsyncGenerator[Event, None]:
        # Patch uuid.uuid4 to use restate's uuid generator
        def new_uuid():
            new_id = self.ctx.uuid()
            return new_id

        uuid.uuid4 = new_uuid

        # Run the agent
        return super().run_async(*args, **kwargs)
