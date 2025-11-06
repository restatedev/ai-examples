import uuid

import restate
from typing import Optional, List, AsyncGenerator

from google.adk import Runner
from google.adk.agents import BaseAgent
from google.adk.events import Event
from google.adk.plugins import BasePlugin

from middleware.restate_session_service import RestateSessionService


async def create_restate_runner(ctx, APP_NAME, user_id, agent):
    session_service = RestateSessionService(ctx)
    await session_service.create_session(
        app_name=APP_NAME, user_id=user_id, session_id=ctx.key()
    )

    runner = RestateRunner(
        restate_context=ctx,
        agent=agent,
        app_name=APP_NAME,
        session_service=session_service,
    )
    return runner




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
