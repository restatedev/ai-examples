# pylint: disable=C0116
"""Simplified hybrid middleware that combines Google A2A SDK with Restate durability."""

import logging
from collections.abc import AsyncIterable, Iterable
from datetime import datetime
from typing import Any, Dict, Optional

import restate
from a2a.server.apps import A2AStarletteApplication
from a2a.server.context import ServerCallContext
from a2a.server.request_handlers import RequestHandler, DefaultRequestHandler
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskStore, TaskUpdater
from a2a.types import (
    Task,
    TaskState,
    TaskStatus,
    AgentCard,
    Message,
    Part,
    TextPart,
    Artifact,
    Role,
    JSONRPCRequest,
    JSONRPCResponse,
    JSONRPCError,
)
from pydantic import ValidationError
from restate.serde import PydanticJsonSerde

from .a2a_middleware import A2AAgent, AgentInvokeResult

logger = logging.getLogger(__name__)

# K/V stored in Restate
TASK = "task"
INVOCATION_ID = "invocation-id"


class RestateTaskStore(TaskStore):
    """Task store implementation that uses Restate for persistence."""

    def __init__(self, task_object_name: str):
        self.task_object_name = task_object_name

    async def save(self, task: Task, context: ServerCallContext | None = None) -> None:
        """Save task to Restate storage - not directly implemented as it's handled by virtual object."""
        pass

    async def get(self, task_id: str, context: ServerCallContext | None = None) -> Task | None:
        """Get task from Restate storage - not directly implemented as it's handled by virtual object."""
        return None

    async def delete(self, task_id: str, context: ServerCallContext | None = None) -> None:
        """Delete task from Restate storage."""
        pass


class RestateAgentExecutor(AgentExecutor):
    """Agent executor that uses Restate for durable execution."""

    def __init__(self, agent: A2AAgent, task_object_name: str):
        self.agent = agent
        self.task_object_name = task_object_name

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Execute agent with Restate durability."""
        logger.info("Hybrid executor delegating to Restate handlers")

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> Optional[Task]:
        """Cancel task execution."""
        logger.info("Hybrid executor delegating cancellation to Restate")
        return None


class RestateAgentMiddleware(Iterable[restate.Service | restate.VirtualObject]):
    """Simplified hybrid middleware that combines Google A2A SDK with Restate durability."""

    def __init__(self, agent_card: AgentCard, agent: A2AAgent):
        self.agent_card = agent_card.model_copy()
        self.agent = agent
        self.a2a_server_name = f"{self.agent_card.name}A2AServer"
        self.task_object_name = f"{self.agent_card.name}TaskObject"

        # Replace the base url with the exact url of the process_request handler
        restate_base_url = self.agent_card.url
        process_request_url = f"{restate_base_url}/{self.a2a_server_name}/process_request"
        self.agent_card.url = process_request_url

        self.restate_services = []
        self._build_services()

        # Set up A2A SDK components
        self.task_store = RestateTaskStore(self.task_object_name)
        self.agent_executor = RestateAgentExecutor(agent, self.task_object_name)

    def __iter__(self):
        """Returns the services that define the agent's a2a server and task object."""
        return iter(self.restate_services)

    @property
    def agent_card_json(self):
        """Return the agent card in A2A SDK compatible format."""
        return self.agent_card.model_dump()

    @property
    def services(self) -> Iterable[restate.Service | restate.VirtualObject]:
        """Return the services that define the agent's a2a server and task object."""
        return self.restate_services

    def _build_services(self):
        """Creates services for Restate integration with A2A SDK compatibility."""
        a2a_service = restate.Service(
            self.a2a_server_name,
            description=self.agent_card.description,
            metadata={
                "agent": self.agent_card.name,
                "version": self.agent_card.version,
            },
        )
        self.restate_services.append(a2a_service)

        task_object = restate.VirtualObject(self.task_object_name)
        self.restate_services.append(task_object)

        agent = self.agent

        class TaskObject:
            """TaskObject with A2A SDK compatibility."""

            @staticmethod
            @task_object.handler(kind="shared")
            async def get_invocation_id(ctx: restate.ObjectSharedContext) -> str | None:
                task_id = ctx.key()
                logger.info("Getting invocation id for task %s", task_id)
                return await ctx.get(INVOCATION_ID) or None

            @staticmethod
            @task_object.handler(output_serde=PydanticJsonSerde(Task), kind="shared")
            async def get_task(ctx: restate.ObjectSharedContext) -> Task | None:
                task_id = ctx.key()
                logger.info("Getting task %s", task_id)
                return await ctx.get(TASK, type_hint=Task) or None

            @staticmethod
            @task_object.handler()
            async def handle_send_task_request_hybrid(
                ctx: restate.ObjectContext, request_data: Dict[str, Any]
            ) -> Dict[str, Any]:
                """Handle task request with hybrid A2A SDK + Restate approach."""
                logger.info("Starting hybrid task execution for request %s", request_data.get("id"))

                # Extract task parameters
                task_id = request_data["params"]["id"]
                session_id = request_data["params"].get("sessionId")
                if not session_id:
                    session_id = str(ctx.uuid())

                # Store invocation ID for cancellation
                await TaskObject.set_invocation_id(ctx, ctx.request().id)

                # Create message from request data
                message_data = request_data["params"]["message"]
                message = Message(
                    role=Role(message_data.get("role", "user")),
                    parts=message_data.get("parts", []),
                    message_id=message_data.get("message_id", str(ctx.uuid())),
                )

                # Create initial task
                task = await TaskObject.upsert_task(ctx, task_id, session_id, message)

                try:
                    # Invoke agent with durability
                    result = await agent.invoke(
                        ctx,
                        query=_get_user_query_from_message(message),
                        session_id=session_id,
                    )

                    if result.require_user_input:
                        updated_task = await TaskObject.update_store(
                            ctx,
                            state=TaskState.INPUT_REQUIRED,
                            status_message=Message(
                                message_id=str(ctx.uuid()),
                                role=Role.agent,
                                parts=result.parts
                            ),
                        )
                    else:
                        updated_task = await TaskObject.update_store(
                            ctx,
                            state=TaskState.COMPLETED,
                            artifacts=[Artifact(artifact_id=str(ctx.uuid()), parts=result.parts)],
                        )

                    ctx.clear(INVOCATION_ID)

                    return {
                        "jsonrpc": "2.0",
                        "id": request_data["id"],
                        "result": updated_task.model_dump(),
                    }

                except restate.exceptions.TerminalError as e:
                    if e.status_code == 409 and e.message == "cancelled":
                        logger.info("Task %s was cancelled", task_id)
                        cancelled_task = await TaskObject.update_store(
                            ctx, state=TaskState.CANCELED
                        )
                        ctx.clear(INVOCATION_ID)
                        return {
                            "jsonrpc": "2.0",
                            "id": request_data["id"],
                            "result": cancelled_task.model_dump(),
                        }

                    logger.error("Error processing task %s: %s", task_id, e)
                    failed_task = await TaskObject.update_store(ctx, state=TaskState.FAILED)
                    ctx.clear(INVOCATION_ID)
                    return {
                        "jsonrpc": "2.0",
                        "id": request_data["id"],
                        "result": failed_task.model_dump(),
                    }

            @staticmethod
            async def update_store(
                ctx: restate.ObjectContext,
                state: TaskState | None,
                status_message: Message | None = None,
                artifacts: list[Artifact] | None = None,
            ) -> Task:
                """Update task store using A2A SDK types."""
                task_id = ctx.key()
                logger.info("Updating status task %s to %s", task_id, state)

                task = await ctx.get(TASK, type_hint=Task)
                if task is None:
                    logger.error("Task %s not found for updating", task_id)
                    raise restate.exceptions.TerminalError(f"Task {task_id} not found")

                new_task_status = await ctx.run_typed(
                    "task status",
                    lambda task_state=state: TaskStatus(
                        state=task_state,
                        timestamp=datetime.now().isoformat(),
                        message=status_message,
                    ),
                    restate.RunOptions(type_hint=TaskStatus),
                )
                prev_status = task.status
                if prev_status.message is not None:
                    task.history.append(prev_status.message)
                task.status = new_task_status

                if artifacts is not None:
                    if task.artifacts is None:
                        task.artifacts = []
                    task.artifacts.extend(artifacts)

                ctx.set(TASK, task)
                return task

            @staticmethod
            async def set_invocation_id(ctx: restate.ObjectContext, invocation_id: str):
                """Set invocation ID for cancellation."""
                task_id = ctx.key()
                logger.info("Adding invocation id %s for task %s", invocation_id, task_id)
                current_invocation_id = await ctx.get(INVOCATION_ID)
                if current_invocation_id is not None:
                    raise restate.exceptions.TerminalError(
                        "There is an ongoing invocation. How did we end up here?"
                    )
                ctx.set(INVOCATION_ID, invocation_id)

            @staticmethod
            async def upsert_task(ctx: restate.ObjectContext, task_id: str, session_id: str, message: Message) -> Task:
                """Upsert task using A2A SDK types."""
                logger.info("Upserting task %s", task_id)

                task_state = await ctx.get(TASK, type_hint=Task)
                if task_state is None:
                    task_state = await ctx.run_typed(
                        "Create task",
                        lambda: Task(
                            id=task_id,
                            context_id=session_id,
                            status=TaskStatus(
                                state=TaskState.SUBMITTED,
                                timestamp=datetime.now().isoformat()
                            ),
                            history=[message] if message else [],
                        ),
                        restate.RunOptions(type_hint=Task)
                    )
                else:
                    task_state.history.append(message)

                ctx.set(TASK, task_state)
                return task_state

        class A2aService:
            """A2A Service with SDK compatibility."""

            @a2a_service.handler()
            @staticmethod
            async def process_request(ctx: restate.Context, request_data: Dict[str, Any]) -> Dict[str, Any]:
                """Process A2A request using hybrid approach."""
                try:
                    method = request_data.get("method")

                    if method == "tasks/send":
                        return await ctx.object_call(
                            TaskObject.handle_send_task_request_hybrid,
                            key=request_data["params"]["id"],
                            arg=request_data,
                            idempotency_key=str(request_data["id"]),
                        )
                    elif method == "tasks/get":
                        task = await ctx.object_call(
                            TaskObject.get_task,
                            key=request_data["params"]["id"],
                            arg=None,
                        )
                        if task is None:
                            return {
                                "jsonrpc": "2.0",
                                "id": request_data["id"],
                                "error": {
                                    "code": -32001,
                                    "message": "Task not found",
                                },
                            }
                        return {
                            "jsonrpc": "2.0",
                            "id": request_data["id"],
                            "result": task.model_dump(),
                        }
                    else:
                        return {
                            "jsonrpc": "2.0",
                            "id": request_data["id"],
                            "error": {
                                "code": -32601,
                                "message": "Method not found",
                            },
                        }

                except Exception as e:
                    logger.error("Error processing hybrid request: %s", e)
                    return {
                        "jsonrpc": "2.0",
                        "id": request_data.get("id"),
                        "error": {
                            "code": -32603,
                            "message": str(e),
                        },
                    }

        return a2a_service, task_object


def _get_user_query_from_message(message: Message) -> str:
    """Extract user query from A2A SDK Message."""
    if not message.parts:
        raise restate.exceptions.TerminalError("Message has no parts")

    part = message.parts[0]

    if not isinstance(part.root, TextPart):
        raise restate.exceptions.TerminalError("Only text parts are supported")
    return part.root.text