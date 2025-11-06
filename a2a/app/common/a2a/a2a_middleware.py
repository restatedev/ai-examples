# pylint: disable=C0116
import json
import logging
from collections.abc import Iterable
from datetime import datetime
from typing import AsyncIterable

import restate
from a2a.types import *
from pydantic_core._pydantic_core import ValidationError
from restate.serde import PydanticJsonSerde

from .models import A2AAgent

logger = logging.getLogger(__name__)

# K/V stored in Restate
TASK = "task"
INVOCATION_ID = "invocation-id"

# Method-to-model mapping for centralized routing
A2ARequestModel = (
        SendMessageRequest
        | SendStreamingMessageRequest
        | GetTaskRequest
        | CancelTaskRequest
        | SetTaskPushNotificationConfigRequest
        | GetTaskPushNotificationConfigRequest
        | ListTaskPushNotificationConfigRequest
        | DeleteTaskPushNotificationConfigRequest
        | TaskResubscriptionRequest
        | GetAuthenticatedExtendedCardRequest
)

METHOD_TO_MODEL: dict[str, type[A2ARequestModel]] = {
    model.model_fields['method'].default: model
    for model in A2ARequestModel.__args__
}


class RestateA2AMiddleware(Iterable[restate.Service | restate.VirtualObject]):
    """Middleware for the agent to handle task processing and state management."""

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
        self._build_services()


    def __iter__(self):
        """Returns the services that define the agent's a2a server and task object."""
        return iter(self.restate_services)

    @property
    def agent_card_json(self):
        """Return the agent card"""
        return self.agent_card.model_dump()

    @property
    def services(self) -> Iterable[restate.Service | restate.VirtualObject]:
        """Return the services that define the agent's a2a server and task object."""
        return self.restate_services

    def _build_services(self):
        """Creates an A2A server for reimbursement processing with customizable name and description."""
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
            """TaskObject is a virtual object that handles task processing and state management."""

            @staticmethod
            @task_object.handler(kind="shared")
            async def get_invocation_id(
                ctx: restate.ObjectSharedContext,
            ) -> str | None:
                task_id = ctx.key()
                logger.info("Getting invocation id for task %s", task_id)
                return await ctx.get(INVOCATION_ID) or None

            @staticmethod
            @task_object.handler(output_serde=PydanticJsonSerde(Task), kind="shared")
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
                success_response = CancelTaskSuccessResponse(
                    id=request.id, result=cancelled_task
                )
                return CancelTaskResponse(root=success_response)

            @staticmethod
            @task_object.handler()
            async def handle_send_message_request(
                ctx: restate.ObjectContext, request: SendMessageRequest
            ) -> SendMessageResponse:
                logger.info(
                    "Starting task execution workflow %s for task %s",
                    request.id,
                    request.params.message.task_id,
                )

                message_send_params: MessageSendParams = request.params
                if not message_send_params.message.context_id:
                    context_id = str(ctx.uuid())
                    message_send_params.message.context_id = context_id

                # Store this invocation ID so it can be cancelled by someone else
                await TaskObject.set_invocation_id(ctx, ctx.request().id)

                # Persist the request data
                await TaskObject.upsert_task(ctx, message_send_params)

                try:
                    # Forward the request to the agent
                    result = await agent.invoke(
                        ctx,
                        query=_get_user_query_from_message(message_send_params.message),
                        session_id=message_send_params.message.context_id,
                    )
                    if result.require_user_input:
                        updated_task = await TaskObject.update_store(
                            ctx,
                            state=TaskState.INPUT_REQUIRED,
                            status_message=Message(message_id=str(ctx.uuid()), role=Role.agent, parts=result.parts),
                        )
                    else:
                        updated_task = await TaskObject.update_store(
                            ctx,
                            state=TaskState.COMPLETED,
                            artifacts=[Artifact(artifact_id=str(ctx.uuid()), parts=result.parts)],
                        )

                    ctx.clear(INVOCATION_ID)
                    return SendMessageResponse(root=SendMessageSuccessResponse(id=request.id, result=updated_task))
                except restate.exceptions.TerminalError as e:
                    if e.status_code == 409 and e.message == "cancelled":
                        logger.info("Task %s was cancelled", message_send_params.id)
                        cancelled_task = await TaskObject.update_store(
                            ctx, state=TaskState.CANCELED
                        )
                        ctx.clear(INVOCATION_ID)
                        return SendMessageResponse(root=SendMessageSuccessResponse(id=request.id, result=cancelled_task))

                    logger.error(
                        "Error while processing task %s: %s - %s",
                        message_send_params.message.message_id,
                        e.status_code,
                        e.message,
                    )
                    failed_task = await TaskObject.update_store(ctx, state=TaskState.FAILED)
                    ctx.clear(INVOCATION_ID)
                    return SendMessageResponse(root=JSONRPCErrorResponse(id=request.id, error=JSONRPCError(code=e.status_code,message=e.message)))

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
                """Set invocation ID."""
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
                ctx: restate.ObjectContext, message_send_params: MessageSendParams
            ) -> Task:
                task_id = ctx.key()
                logger.info("Upserting task %s", task_id)

                task_state = await ctx.get(TASK, type_hint=Task)
                if task_state is None:
                    task_state = await ctx.run_typed(
                        "Create task",
                        lambda: Task(
                            id=message_send_params.message.message_id,
                            context_id=message_send_params.message.context_id,
                            status=TaskStatus(
                                state=TaskState.SUBMITTED,
                                timestamp=datetime.now().isoformat()
                            ),
                            history=[message_send_params.message] if message_send_params.message else [],
                        ),
                        restate.RunOptions(type_hint=Task)
                    )
                else:
                    task_state.history.append(message_send_params.message)

                ctx.set(TASK, task_state)
                return task_state

        class A2aService:

            @a2a_service.handler()
            @staticmethod
            async def process_request(
                ctx: restate.Context, req: JSONRPCRequest
            ) -> JSONRPCResponse:
                methods = {
                    SendMessageRequest: A2aService.on_send_message_request,
                    SendStreamingMessageRequest: A2aService.on_send_streaming_message_request,
                    GetTaskRequest: A2aService.on_get_task,
                    CancelTaskRequest: A2aService.on_cancel_task,
                    TaskResubscriptionRequest: A2aService.on_resubscribe_to_task,
                    SetTaskPushNotificationConfigRequest: A2aService.on_set_task_push_notification,
                    GetTaskPushNotificationConfigRequest: A2aService.on_get_task_push_notification,
                    ListTaskPushNotificationConfigRequest: A2aService.on_list_task_push_notification,
                    DeleteTaskPushNotificationConfigRequest: A2aService.on_delete_task_push_notification,
                    GetAuthenticatedExtendedCardRequest: A2aService.on_get_authenticated_extended_card_request
                }

                method = req.method

                model_class = METHOD_TO_MODEL.get(method)
                if not model_class:
                    return JSONRPCResponse(root=JSONRPCErrorResponse(
                        id=req.id, error=MethodNotFoundError()
                    ))
                try:
                    json_rpc_request = model_class.model_validate_json(req.model_dump_json())
                except ValidationError as e:
                    logger.exception('Failed to validate base JSON-RPC request')
                    return JSONRPCResponse(root=JSONRPCErrorResponse(
                        id=req.id, error=InvalidParamsError(data=json.loads(e.json()))
                    ))

                fn = methods.get(type(json_rpc_request), None)
                if not fn:
                    return JSONRPCResponse(root=JSONRPCErrorResponse(
                        id=req.id,
                        error=MethodNotFoundError(message="Method not found"),
                    ))
                try:
                    return await fn(ctx, json_rpc_request)
                except restate.exceptions.TerminalError as e:
                    logger.error("Error processing request: %s", e)
                    return JSONRPCResponse(root=JSONRPCErrorResponse(
                        id=req.id,
                        error=JSONRPCError(code=e.status_code, message=e.message),
                    ))

            @staticmethod
            async def on_send_message_request(
                ctx: restate.Context, request: SendMessageRequest
            ) -> SendMessageResponse:
                task_id = request.params.message.task_id
                logger.info("Processing send message request with id %s for task id %s", request.id, task_id)

                if task_id is not None and not (isinstance(task_id, str) and task_id):
                    raise restate.TerminalError('Task ID must be a non-empty string')
                return await ctx.object_call(
                    TaskObject.handle_send_message_request,
                    key=task_id or str(ctx.uuid()),
                    arg=request,
                    idempotency_key=str(request.id),
                )

            @staticmethod
            async def on_send_streaming_message_request(
                    ctx: restate.Context, request: SendStreamingMessageRequest
            ) -> SendStreamingMessageResponse:
                raise restate.exceptions.TerminalError(f"Not implemented: {request.method}")


            @staticmethod
            async def on_get_task(
                ctx: restate.Context, request: GetTaskRequest
            ) -> GetTaskResponse:
                logger.info("Getting task %s", request.params.id)
                task_query_params: TaskQueryParams = request.params

                task = await ctx.object_call(
                    TaskObject.get_task, key=task_query_params.id, arg=None
                )
                if task is None:
                    return GetTaskResponse(root=JSONRPCErrorResponse(id=request.id, error=TaskNotFoundError()))

                task_result = task.model_copy()
                history_length = task_query_params.historyLength
                if history_length is not None and history_length > 0:
                    task_result.history = task.history[-history_length:]
                else:
                    # Default is no history
                    task_result.history = []
                return GetTaskResponse(root=GetTaskSuccessResponse(id=request.id, result=task_result))

            @staticmethod
            async def on_cancel_task(
                ctx: restate.Context, request: CancelTaskRequest
            ) -> CancelTaskResponse:
                logger.info("Cancelling task %s", request.params.id)
                task_id_params: TaskIdParams = request.params

                task = await ctx.object_call(
                    TaskObject.get_task, key=task_id_params.id, arg=None
                )
                if task is None:
                    return CancelTaskResponse(root=JSONRPCErrorResponse(id=request.id, error=TaskNotFoundError()))
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
                    invocation_id, type_hint=SendMessageResponse
                )
                return CancelTaskResponse(root=CancelTaskSuccessResponse(
                    id=request.id,
                    result=canceled_task_info.result,
                ))

            @staticmethod
            async def on_set_task_push_notification(
                ctx: restate.Context, request: SetTaskPushNotificationConfigRequest
            ) -> SetTaskPushNotificationConfigResponse:
                return SetTaskPushNotificationConfigResponse(root=JSONRPCErrorResponse(id=request.id, error=PushNotificationNotSupportedError()))

            @staticmethod
            async def on_get_task_push_notification(
                ctx: restate.Context, request: GetTaskPushNotificationConfigRequest
            ) -> GetTaskPushNotificationConfigResponse:
                return GetTaskPushNotificationConfigResponse(root=JSONRPCErrorResponse(id=request.id, error=PushNotificationNotSupportedError()))

            @staticmethod
            async def on_list_task_push_notification(
                ctx: restate.Context, request: ListTaskPushNotificationConfigRequest
            ) -> ListTaskPushNotificationConfigResponse:
                return ListTaskPushNotificationConfigResponse(root=JSONRPCErrorResponse(id=request.id, error=PushNotificationNotSupportedError()))

            @staticmethod
            async def on_delete_task_push_notification(
                ctx: restate.Context, request: DeleteTaskPushNotificationConfigRequest
            ) -> DeleteTaskPushNotificationConfigResponse:
                return DeleteTaskPushNotificationConfigResponse(root=JSONRPCErrorResponse(id=request.id, error=PushNotificationNotSupportedError()))

            @staticmethod
            async def on_resubscribe_to_task(
                ctx: restate.Context, request: TaskResubscriptionRequest
            ) -> AsyncIterable[SendMessageResponse] | JSONRPCResponse:
                return JSONRPCResponse(root=JSONRPCErrorResponse(id=request.id, error=UnsupportedOperationError()))

            @staticmethod
            async def on_get_authenticated_extended_card_request(
                ctx: restate.Context, request: GetAuthenticatedExtendedCardRequest
            ) -> GetAuthenticatedExtendedCardResponse:
                return GetAuthenticatedExtendedCardResponse(root=JSONRPCErrorResponse(id=request.id, error=AuthenticatedExtendedCardNotConfiguredError()))

        return a2a_service, task_object


def _get_user_query_from_message(message: Message) -> str:
    """Extract user query from A2A SDK Message."""
    if not message.parts:
        raise restate.exceptions.TerminalError("Message has no parts")

    part = message.parts[0]

    if not isinstance(part.root, TextPart):
        raise restate.exceptions.TerminalError("Only text parts are supported")
    return part.root.text