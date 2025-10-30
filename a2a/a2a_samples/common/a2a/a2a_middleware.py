# pylint: disable=C0116
import logging
import uuid
import restate

from collections.abc import AsyncIterable, Iterable
from datetime import datetime
from pydantic import ValidationError
from restate.serde import PydanticJsonSerde

from a2a.types import (
    AgentCard,
    Message,
    Part,
    Task,
    TaskState,
    TaskStatus,
    TextPart,
    DataPart,
    FilePart,
    Artifact,
    Role,
    AgentSkill,
    AgentCapabilities,
    CancelTaskResponse,
    CancelTaskRequest,
    GetTaskRequest,
    GetTaskResponse,
    TaskQueryParams,
    TaskNotFoundError,
    TaskIdParams,
    JSONRPCResponse,
    JSONRPCError,
    JSONRPCRequest,
    SendMessageRequest,
    SendMessageResponse,
    MessageSendParams,
    SetTaskPushNotificationConfigRequest,
    SetTaskPushNotificationConfigResponse,
    GetTaskPushNotificationConfigRequest,
    GetTaskPushNotificationConfigResponse,
    TaskResubscriptionRequest,
)

from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

# K/V stored in Restate
TASK = "task"
INVOCATION_ID = "invocation-id"


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


class AgentMiddleware(Iterable[restate.Service | restate.VirtualObject]):
    """Middleware for the agent to handle task processing and state management using A2A SDK types."""

    def __init__(self, agent_card: AgentCard, agent: A2AAgent):
        self.agent_card = agent_card.model_copy()
        self.agent = agent
        self.a2a_server_name = f"{self.agent_card.name}A2AServer"
        self.task_object_name = f"{self.agent_card.name}TaskObject"

        # replace the base url with the exact url of the process_request handler.
        restate_base_url = self.agent_card.url
        process_request_url = (
            f"{restate_base_url}/{self.a2a_server_name}/process_request"
        )
        self.agent_card.url = process_request_url

        self.restate_services = []
        _build_services(self)

    def __iter__(self):
        """Returns the services that define the agent's a2a server and task object."""
        return iter(self.restate_services)

    @property
    def agent_card_json(self):
        """Return the agent card"""
        return self.agent_card.model_dump()

    @property
    def services(self) -> Iterable[restate.Service | restate.VirtualObject]:
        """Return the services that define the agent's a2a server and task object"""
        return self.restate_services


def _build_services(middleware: AgentMiddleware):
    """Creates an A2A server for processing with A2A SDK types."""
    a2a_service = restate.Service(
        middleware.a2a_server_name,
        description=middleware.agent_card.description,
        metadata={
            "agent": middleware.agent_card.name,
            "version": middleware.agent_card.version,
        },
    )
    middleware.restate_services.append(a2a_service)

    task_object = restate.VirtualObject(middleware.task_object_name)
    middleware.restate_services.append(task_object)

    agent = middleware.agent

    class TaskObject:
        """TaskObject handles task processing using A2A SDK types."""

        @staticmethod
        @task_object.handler(kind="shared")
        async def get_invocation_id(
            ctx: restate.ObjectSharedContext,
        ) -> str | None:
            task_id = ctx.key()
            logger.info("Getting invocation id for task %s", task_id)
            return await ctx.get(INVOCATION_ID) or None

        @staticmethod
        @task_object.handler(kind="shared")
        async def get_task(
            ctx: restate.ObjectSharedContext,
        ) -> Task | None:
            task_id = ctx.key()
            logger.info("Getting task %s", task_id)
            return await ctx.get(TASK, type_hint=Task) or None

        @staticmethod
        @task_object.handler()
        async def cancel_task(
            ctx: restate.ObjectContext, request: CancelTaskRequest
        ) -> CancelTaskResponse:
            cancelled_task = await TaskObject.update_store(
                ctx, state=TaskState.CANCELED
            )
            return CancelTaskResponse(id=request.id, result=cancelled_task)

        @staticmethod
        @task_object.handler()
        async def handle_send_message_request(
            ctx: restate.ObjectContext, request: SendMessageRequest
        ) -> SendMessageResponse:
            logger.info(
                "Starting task execution workflow %s for task %s",
                request.id,
                request.params.id,
            )

            task_send_params = request.params
            if not task_send_params.sessionId:
                session_id = str(ctx.uuid())
                task_send_params.sessionId = session_id

            # Store this invocation ID so it can be cancelled by someone else
            await TaskObject.set_invocation_id(ctx, ctx.request().id)

            # Persist the request data
            await TaskObject.upsert_task(ctx, task_send_params)

            try:
                # Forward the request to the agent
                result = await agent.invoke(
                    ctx,
                    query=_get_user_query(task_send_params),
                    session_id=task_send_params.sessionId,
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
                        artifacts=[Artifact(parts=result.parts)],
                    )

                ctx.clear(INVOCATION_ID)
                return SendTaskResponse(id=request.id, result=updated_task)
            except restate.exceptions.TerminalError as e:
                if e.status_code == 409 and e.message == "cancelled":
                    logger.info("Task %s was cancelled", task_send_params.id)
                    cancelled_task = await TaskObject.update_store(
                        ctx, state=TaskState.CANCELED
                    )
                    ctx.clear(INVOCATION_ID)
                    return SendTaskResponse(id=request.id, result=cancelled_task)

                logger.error(
                    "Error while processing task %s: %s - %s",
                    task_send_params.id,
                    e.status_code,
                    e.message,
                )
                failed_task = await TaskObject.update_store(ctx, state=TaskState.FAILED)
                ctx.clear(INVOCATION_ID)
                return SendTaskResponse(id=request.id, result=failed_task)

        @staticmethod
        async def update_store(
            ctx: restate.ObjectContext,
            state: TaskState | None,
            status_message: Message | None = None,
            artifacts: list[Artifact] | None = None,
        ) -> Task:
            task_id = ctx.key()
            logger.info("Updating status task %s to %s", task_id, state)

            task = await ctx.get(TASK, type_hint=Task)
            if task is None:
                logger.error("Task %s not found for updating the task", task_id)
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
            task_id = ctx.key()
            logger.info("Adding invocation id %s for task %s", invocation_id, task_id)
            current_invocation_id = await ctx.get(INVOCATION_ID)
            if current_invocation_id is not None:
                raise restate.exceptions.TerminalError(
                    "There is an ongoing invocation. How did we end up here?"
                )
            ctx.set(INVOCATION_ID, invocation_id)

        @staticmethod
        async def upsert_task(
            ctx: restate.ObjectContext, task_send_params
        ) -> Task:
            task_id = ctx.key()
            logger.info("Upserting task %s", task_id)

            task_state = await ctx.get(TASK, type_hint=Task)
            if task_state is None:
                task_state = await ctx.run_typed(
                    "Create task",
                    lambda run_params=task_send_params: Task(
                        id=run_params.id,
                        context_id=run_params.sessionId,
                        status=TaskStatus(
                            state=TaskState.SUBMITTED,
                            timestamp=datetime.now().isoformat()
                        ),
                        history=[run_params.message] if run_params.message else [],
                    ),
                    restate.RunOptions(type_hint=Task)
                )
            else:
                task_state.history.append(task_send_params.message)

            ctx.set(TASK, task_state)
            return task_state

    class A2aService:
        @a2a_service.handler()
        @staticmethod
        async def process_request(
            ctx: restate.Context, req: JSONRPCRequest
        ) -> JSONRPCResponse:
            methods = {
                "tasks/get": A2aService.on_get_task,
                "message/send": A2aService.on_send_message_request,
                "tasks/cancel": A2aService.on_cancel_task,
                "tasks/pushNotification/set": A2aService.on_set_task_push_notification,
                "tasks/pushNotification/get": A2aService.on_get_task_push_notification,
            }

            try:
                # Validate the JSON-RPC request format
                if not req.method:
                    return JSONRPCResponse(
                        id=req.id,
                        error=JSONRPCError(code=400, message="Missing method"),
                    )

                fn = methods.get(req.method, None)
                if not fn:
                    return JSONRPCResponse(
                        id=req.id,
                        error=JSONRPCError(code=-32601, message="Method not found"),
                    )

                # Create the appropriate request object based on method
                if req.method == "message/send":
                    request_obj = SendMessageRequest(id=req.id, params=req.params)
                elif req.method == "tasks/get":
                    request_obj = GetTaskRequest(id=req.id, params=req.params)
                elif req.method == "tasks/cancel":
                    request_obj = CancelTaskRequest(id=req.id, params=req.params)
                else:
                    return JSONRPCResponse(
                        id=req.id,
                        error=JSONRPCError(code=-32601, message="Method not implemented"),
                    )

                return await fn(ctx, request_obj)
            except ValidationError as e:
                logger.error("Error validating request: %s", e)
                return JSONRPCResponse(
                    id=req.id,
                    error=JSONRPCError(code=400, message="Invalid request format"),
                )
            except restate.exceptions.TerminalError as e:
                logger.error("Error processing request: %s", e)
                return JSONRPCResponse(
                    id=req.id,
                    error=JSONRPCError(code=e.status_code, message=e.message),
                )

        @staticmethod
        async def on_send_message_request(
            ctx: restate.Context, request: SendMessageRequest
        ) -> SendMessageResponse:
            logger.info("Sending message %s", request.id)

            # Extract task ID from message metadata or generate one
            task_id = str(request.id)  # Use request ID as task ID

            return await ctx.object_call(
                TaskObject.handle_send_message_request,
                key=task_id,
                arg=request,
                idempotency_key=str(request.id),
            )

        @staticmethod
        async def on_get_task(
            ctx: restate.Context, request: GetTaskRequest
        ) -> GetTaskResponse:
            logger.info("Getting task %s", request.params.id)
            task_query_params = request.params

            task = await ctx.object_call(
                TaskObject.get_task, key=task_query_params.id, arg=None
            )
            if task is None:
                return GetTaskResponse(id=request.id, error=TaskNotFoundError())

            task_result = task.model_copy()
            history_length = task_query_params.historyLength
            if history_length is not None and history_length > 0:
                task_result.history = task.history[-history_length:]
            else:
                # Default is no history
                task_result.history = []
            return GetTaskResponse(id=request.id, result=task_result)

        @staticmethod
        async def on_cancel_task(
            ctx: restate.Context, request: CancelTaskRequest
        ) -> CancelTaskResponse:
            logger.info("Cancelling task %s", request.params.id)
            task_id_params = request.params

            task = await ctx.object_call(
                TaskObject.get_task, key=task_id_params.id, arg=None
            )
            if task is None:
                return CancelTaskResponse(id=request.id, error=TaskNotFoundError())
            invocation_id = await ctx.object_call(
                TaskObject.get_invocation_id, key=task_id_params.id, arg=None
            )
            if invocation_id is None:
                # Task either doesn't exist or is already completed
                return await ctx.object_call(
                    TaskObject.cancel_task, key=task_id_params.id, arg=request
                )

            # Cancel the invocation
            ctx.cancel_invocation(invocation_id)
            # Wait for cancellation to complete and for the cancelled task info
            canceled_task_info = await ctx.attach_invocation(
                invocation_id, type_hint=SendTaskResponse
            )
            return CancelTaskResponse(
                id=request.id,
                result=canceled_task_info.result,
            )

        @staticmethod
        async def on_set_task_push_notification(
            ctx: restate.Context, request: SetTaskPushNotificationRequest
        ) -> SetTaskPushNotificationResponse:
            raise restate.exceptions.TerminalError(f"Not implemented: {request.method}")

        @staticmethod
        async def on_get_task_push_notification(
            ctx: restate.Context, request: GetTaskPushNotificationRequest
        ) -> GetTaskPushNotificationResponse:
            raise restate.exceptions.TerminalError(f"Not implemented: {request.method}")

        @staticmethod
        async def on_send_task_subscribe(
            ctx: restate.Context, request: SendTaskStreamingRequest
        ) -> AsyncIterable[SendTaskStreamingResponse] | JSONRPCResponse:
            raise restate.exceptions.TerminalError(f"Not implemented: {request.method}")

    return a2a_service, task_object


def _get_user_query(task_send_params) -> str:
    part = task_send_params.message.parts[0]
    if not isinstance(part, TextPart):
        raise restate.exceptions.TerminalError("Only text parts are supported")
    return part.text