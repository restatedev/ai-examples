from typing import Optional, Any, override

import restate
from google.adk.sessions import Session
from google.adk.events.event import Event
from google.adk.sessions.base_session_service import (
    BaseSessionService,
    ListSessionsResponse,
    GetSessionConfig,
)


# Translation layer between Restate's K/V store and ADK's session service interface.
class RestateSessionService(BaseSessionService):

    def __init__(self, ctx: restate.ObjectContext):
        self.ctx = ctx

    async def create_session(
        self,
        app_name: str,
        user_id: str,
        state: Optional[dict[str, Any]] = None,
        session_id: Optional[str] = None,
    ) -> Session:

        if session_id is None:
            raise restate.TerminalError("No session ID provided.")

        session = await self.ctx.get("session", type_hint=Session) or Session(
            app_name=app_name,
            user_id=user_id,
            id=session_id,
            state=state or {},
        )
        self.ctx.set("session", session)
        return session

    async def get_session(
        self,
        *,
        app_name: str,
        user_id: str,
        session_id: str,
        config: Optional[GetSessionConfig] = None,
    ) -> Optional[Session]:
        return await self.ctx.get("session", type_hint=Session)

    async def list_sessions(
        self, *, app_name: str, user_id: Optional[str] = None
    ) -> ListSessionsResponse:
        sessions = []

        # Get all state keys and filter for session keys
        keys = await self.ctx.state_keys()
        for key in keys:
            if key.startswith(f"session:"):
                session_data = await self.ctx.get(key, type_hint=Session)
                if session_data:
                    sessions.append(session_data)

        return ListSessionsResponse(sessions=sessions)

    async def delete_session(
        self, *, app_name: str, user_id: str, session_id: str
    ) -> None:
        self.ctx.clear("session")

    @override
    async def append_event(self, session: Session, event: Event) -> Event:
        """Appends an event to a session object."""

        # The event has a timestamp that need to be persisted to avoid non-determinism
        event = await self.ctx.run_typed(
            "persist event", lambda: event, restate.RunOptions(type_hint=Event)
        )
        if event.partial:
            return event
        # For now, we also store temp state
        event = self._trim_temp_delta_state(event)
        self._update_session_state(session, event)
        session.events.append(event)

        session_to_store = session.model_copy()
        # Remove restate-specific context that got added by the plugin before storing
        session_to_store.state.pop("restate_context", None)
        self.ctx.set("session", session_to_store)
        return event
