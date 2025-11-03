from typing import Optional, List, AsyncGenerator

from google.adk import Runner
from google.adk.agents import BaseAgent
from google.adk.events import Event
from google.adk.plugins import BasePlugin

from app.utils.restate_session_service import RestateSessionService

from contextlib import contextmanager
import restate
import uuid

@contextmanager
def deterministic_uuid(ctx: restate.ObjectContext):
    original_uuid4 = uuid.uuid4

    # Monkey patch
    try:
        uuid.uuid4 = ctx.uuid
        yield
    finally:
        uuid.uuid4 = original_uuid4


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
        with deterministic_uuid(self.ctx):
            return super().run_async(*args, **kwargs)
