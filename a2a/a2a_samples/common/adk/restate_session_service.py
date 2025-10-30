from typing import Optional, Any, override

import restate
from google.adk.sessions import Session
from google.adk.events.event import Event
from google.adk.sessions.base_session_service import BaseSessionService, ListSessionsResponse, GetSessionConfig


# Translation layer between Restate's K/V store and ADK's session service interface.
class RestateSessionService(BaseSessionService):

    def __init__(self, ctx: restate.ObjectContext):
        self.ctx = ctx


    async def create_session(self, app_name: str, user_id: str, state: Optional[dict[str, Any]] = None,
                             session_id: Optional[str] = None) -> Session:
        if session_id is None:
            session_id = self.ctx.uuid()

        ongoing_session = await self.ctx.get(f'session:{session_id}', type_hint=Session)

        if ongoing_session is not None:
            ongoing_session.state["restate_context"] = self.ctx
            return ongoing_session

        session = Session(
            app_name=app_name,
            user_id=user_id,
            id=session_id,
            state=state or {},
        )
        self.ctx.set(f'session:{session_id}', session)

        session.state["restate_context"] = self.ctx
        return session

    async def get_session(self, *, app_name: str, user_id: str, session_id: str,
                          config: Optional[GetSessionConfig] = None) -> Optional[Session]:
        session_data = await self.ctx.get(f'session:{session_id}', type_hint=Session)

        if session_data is None:
            return None

        session_data.state["restate_context"] = self.ctx
        return session_data

    async def list_sessions(self, *, app_name: str, user_id: Optional[str] = None) -> ListSessionsResponse:
        sessions = []

        # Get all state keys and filter for session keys
        keys = await self.ctx.state_keys()
        for key in keys:
            if key.startswith(f"session:"):
                session_data = await self.ctx.get(key, type_hint=Session)
                if session_data:
                    sessions.append(session_data)

        return ListSessionsResponse(sessions=sessions)

    async def delete_session(self, *, app_name: str, user_id: str, session_id: str) -> None:
        self.ctx.clear(f'session:{session_id}')


    @override
    async def append_event(self, session: Session, event: Event) -> Event:
      """Appends an event to a session object."""
      if event.partial:
        return event
      # For now, we also store temp state
      # event = self._trim_temp_delta_state(event)
      self._update_session_state(session, event)
      session.events.append(event)
      return event

    def _update_session_state(self, session: Session, event: Event) -> None:
        """Updates the session state based on the event."""
        if not event.actions or not event.actions.state_delta:
          return
        for key, value in event.actions.state_delta.items():
          # For now, we also store temp state
          # if key.startswith(State.TEMP_PREFIX):
          #   continue
          session.state.update({key: value})

        session_to_store = session
        session_to_store.state.pop("restate_context", None)
        self.ctx.set(f'session:{session.id}', session_to_store)