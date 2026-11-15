"""A2A 1.x JSON-RPC facade backed by durable Restate virtual objects.

Protobuf messages stay local to each handler. Restate journals and state store
ProtoJSON dictionaries, rather than Python protobuf objects or legacy models.
"""

import logging
from collections.abc import Iterable, Iterator
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import NAMESPACE_URL, uuid5

import restate
from a2a.types import (
    AgentCard,
    Artifact,
    CancelTaskRequest,
    GetTaskRequest,
    Message,
    Part,
    Role,
    SendMessageRequest,
    SendMessageResponse,
    Task,
    TaskState,
    TaskStatus,
)
from a2a.utils.errors import (
    JSON_RPC_ERROR_CODE_MAP,
    A2AError,
    ContentTypeNotSupportedError,
    ExtendedAgentCardNotConfiguredError,
    InternalError,
    InvalidParamsError,
    InvalidRequestError,
    MethodNotFoundError,
    PushNotificationNotSupportedError,
    TaskNotCancelableError,
    TaskNotFoundError,
    UnsupportedOperationError,
    VersionNotSupportedError,
)
from a2a.utils.proto_utils import parse_lenient, validate_proto_required_fields
from google.protobuf.json_format import MessageToDict, ParseDict, ParseError
from packaging.version import InvalidVersion, Version

from .models import A2AAgent

logger = logging.getLogger(__name__)
TASK = "task"
INVOCATION_ID = "invocation-id"
TERMINAL_STATES = {
    TaskState.TASK_STATE_COMPLETED,
    TaskState.TASK_STATE_FAILED,
    TaskState.TASK_STATE_CANCELED,
    TaskState.TASK_STATE_REJECTED,
}
PUSH_METHODS = {
    "CreateTaskPushNotificationConfig",
    "GetTaskPushNotificationConfig",
    "ListTaskPushNotificationConfigs",
    "DeleteTaskPushNotificationConfig",
}


def error_reply(error: A2AError) -> dict[str, Any]:
    value: dict[str, Any] = {
        "code": JSON_RPC_ERROR_CODE_MAP[type(error)],
        "message": error.message,
    }
    if error.data is not None:
        value["data"] = error.data
    return {"error": value}


def parse_request(data: dict[str, Any], model: type) -> Any:
    try:
        request = parse_lenient(data, model())
        validate_proto_required_fields(request)
        return request
    except ParseError as error:
        raise InvalidParamsError(str(error)) from error


def user_query(message: Message) -> str:
    if any(part.WhichOneof("content") is None for part in message.parts):
        raise InvalidParamsError("Each part must contain content")
    if any(part.WhichOneof("content") != "text" for part in message.parts):
        raise ContentTypeNotSupportedError("This example accepts text parts only")
    return "\n".join(part.text for part in message.parts)


def trim_history(task: dict[str, Any], length: int) -> None:
    if length == 0:
        task.pop("history", None)
    elif "history" in task:
        task["history"] = task["history"][-length:]


class RestateA2AMiddleware(Iterable[restate.Service | restate.VirtualObject]):
    """Serve non-streaming A2A tasks using durable Restate execution."""

    def __init__(self, agent_card: AgentCard, agent: A2AAgent) -> None:
        self.agent_card = AgentCard()
        self.agent_card.CopyFrom(agent_card)
        self.agent = agent
        self.a2a_server_name = f"{agent_card.name}A2AServer"
        self.task_object_name = f"{agent_card.name}TaskObject"
        if not self.agent_card.supported_interfaces:
            raise ValueError("Agent card must declare a JSONRPC supported interface")
        for interface in self.agent_card.supported_interfaces:
            if interface.protocol_binding != "JSONRPC":
                raise ValueError("This example supports the JSONRPC binding only")
            interface.url = (
                f"{interface.url.rstrip('/')}/{self.a2a_server_name}/process_request"
            )
            interface.protocol_version = "1.0"
        self.agent_card.capabilities.streaming = False
        self.agent_card.capabilities.push_notifications = False
        validate_proto_required_fields(self.agent_card)
        self.restate_services: list[restate.Service | restate.VirtualObject] = []
        self._build_services()

    def __iter__(self) -> Iterator[restate.Service | restate.VirtualObject]:
        return iter(self.restate_services)

    @property
    def agent_card_json(self) -> dict[str, Any]:
        return MessageToDict(self.agent_card)

    @property
    def services(self) -> Iterable[restate.Service | restate.VirtualObject]:
        return self.restate_services

    def _build_services(self) -> None:
        service = restate.Service(
            self.a2a_server_name,
            description=self.agent_card.description,
            metadata={
                "agent": self.agent_card.name,
                "version": self.agent_card.version,
            },
        )
        task_object = restate.VirtualObject(self.task_object_name)
        self.restate_services.extend([service, task_object])
        agent = self.agent

        async def load_task(
            ctx: restate.ObjectContext | restate.ObjectSharedContext,
        ) -> Task | None:
            value = await ctx.get(TASK, type_hint=dict)
            return ParseDict(value, Task()) if value is not None else None

        async def save_status(
            ctx: restate.ObjectContext,
            task: Task,
            state: TaskState,
            status_message: Message | None = None,
        ) -> None:
            if task.status.HasField("message"):
                task.history.append(task.status.message)
            status = TaskStatus(state=state)
            status.timestamp.FromDatetime(
                datetime.fromtimestamp(await ctx.time(), timezone.utc)
            )
            if status_message is not None:
                status.message.CopyFrom(status_message)
            task.status.CopyFrom(status)
            ctx.set(TASK, MessageToDict(task))

        @task_object.handler(kind="shared")
        async def get_task(ctx: restate.ObjectSharedContext) -> dict | None:
            return await ctx.get(TASK, type_hint=dict)

        @task_object.handler(kind="shared")
        async def get_invocation_id(ctx: restate.ObjectSharedContext) -> str | None:
            return await ctx.get(INVOCATION_ID, type_hint=str)

        @task_object.handler()
        async def cancel_task(ctx: restate.ObjectContext) -> dict:
            task = await load_task(ctx)
            if task is None:
                return error_reply(TaskNotFoundError())
            if task.status.state != TaskState.TASK_STATE_CANCELED:
                if task.status.state in TERMINAL_STATES:
                    return error_reply(TaskNotCancelableError())
                await save_status(ctx, task, TaskState.TASK_STATE_CANCELED)
            ctx.clear(INVOCATION_ID)
            return {"result": MessageToDict(task)}

        @task_object.handler()
        async def run_task(ctx: restate.ObjectContext, data: dict) -> dict:
            request = parse_request(data, SendMessageRequest)
            message = request.message
            task = await load_task(ctx)
            if task is None and message.task_id:
                return error_reply(TaskNotFoundError())
            if task is not None:
                if task.status.state in TERMINAL_STATES:
                    return error_reply(
                        UnsupportedOperationError("Task is already terminal")
                    )
                if message.context_id and message.context_id != task.context_id:
                    return error_reply(
                        InvalidParamsError("contextId does not match the task")
                    )
            else:
                task = Task(
                    id=ctx.key(), context_id=message.context_id or str(ctx.uuid())
                )
            if task.status.HasField("message"):
                task.history.append(task.status.message)
                task.status.ClearField("message")
            message.task_id = task.id
            message.context_id = task.context_id
            task.history.append(message)
            ctx.set(INVOCATION_ID, ctx.request().id)
            await save_status(ctx, task, TaskState.TASK_STATE_WORKING)
            try:
                result = await agent.invoke(ctx, user_query(message), task.context_id)
                parts = [ParseDict(part, Part()) for part in result.parts]
                if not parts or any(
                    part.WhichOneof("content") is None for part in parts
                ):
                    raise restate.TerminalError("Agent returned no content")
                if result.require_user_input:
                    await save_status(
                        ctx,
                        task,
                        TaskState.TASK_STATE_INPUT_REQUIRED,
                        Message(
                            message_id=str(ctx.uuid()),
                            role=Role.ROLE_AGENT,
                            parts=parts,
                        ),
                    )
                else:
                    task.artifacts.append(
                        Artifact(artifact_id=str(ctx.uuid()), parts=parts)
                    )
                    state = (
                        TaskState.TASK_STATE_COMPLETED
                        if result.is_task_complete
                        else TaskState.TASK_STATE_WORKING
                    )
                    await save_status(ctx, task, state)
                ctx.clear(INVOCATION_ID)
                return {"result": MessageToDict(SendMessageResponse(task=task))}
            except (restate.TerminalError, ParseError) as error:
                state = (
                    TaskState.TASK_STATE_CANCELED
                    if isinstance(error, restate.TerminalError)
                    and error.status_code == 409
                    and error.message == "cancelled"
                    else TaskState.TASK_STATE_FAILED
                )
                await save_status(ctx, task, state)
                ctx.clear(INVOCATION_ID)
                if state == TaskState.TASK_STATE_CANCELED:
                    return {"result": MessageToDict(SendMessageResponse(task=task))}
                logger.error("Agent task failed: %s", error)
                return error_reply(InternalError())

        @service.handler()
        async def process_request(ctx: restate.Context, request: dict) -> dict:
            request_id = None
            try:
                if not isinstance(request, dict):
                    raise InvalidRequestError("A request must be an object")
                raw_id = request.get("id")
                if isinstance(raw_id, bool) or not isinstance(raw_id, (str, int)):
                    raise InvalidRequestError(
                        "A request id must be a string or integer"
                    )
                request_id = raw_id
                if request.get("jsonrpc") != "2.0" or not isinstance(
                    request.get("method"), str
                ):
                    raise InvalidRequestError()
                version = ctx.request().headers.get("a2a-version", "")
                try:
                    compatible = Version(version).release[:2] == (1, 0)
                except InvalidVersion:
                    compatible = False
                if not compatible:
                    raise VersionNotSupportedError("Send A2A-Version: 1.0")
                method = request["method"]
                params = request.get("params", {})
                if not isinstance(params, dict):
                    raise InvalidParamsError("params must be an object")
                if method == "SendMessage":
                    parsed = parse_request(params, SendMessageRequest)
                    user_query(parsed.message)
                    if (
                        parsed.configuration.HasField("history_length")
                        and parsed.configuration.history_length < 0
                    ):
                        raise InvalidParamsError("historyLength must not be negative")
                    task_id = parsed.message.task_id or str(
                        uuid5(
                            NAMESPACE_URL,
                            f"{self.task_object_name}:{parsed.message.message_id}",
                        )
                    )
                    result = ctx.object_call(
                        run_task,
                        key=task_id,
                        arg=params,
                        idempotency_key=parsed.message.message_id,
                    )
                    if parsed.configuration.return_immediately:
                        while True:
                            completed, value = await restate.select(
                                result=result,
                                task=ctx.object_call(get_task, key=task_id, arg=None),
                            )
                            if completed == "result":
                                reply = value
                                break
                            # An older task snapshot is not acceptance of this turn.
                            if value is not None and any(
                                message.get("messageId") == parsed.message.message_id
                                for message in value.get("history", [])
                            ):
                                reply = {"result": {"task": value}}
                                break
                            await ctx.sleep(timedelta(milliseconds=20))
                    else:
                        reply = await result
                    if "result" in reply and parsed.configuration.HasField(
                        "history_length"
                    ):
                        trim_history(
                            reply["result"]["task"], parsed.configuration.history_length
                        )
                elif method == "GetTask":
                    parsed = parse_request(params, GetTaskRequest)
                    if parsed.HasField("history_length") and parsed.history_length < 0:
                        raise InvalidParamsError("historyLength must not be negative")
                    task = await ctx.object_call(get_task, key=parsed.id, arg=None)
                    if task is None:
                        raise TaskNotFoundError()
                    if parsed.HasField("history_length"):
                        trim_history(task, parsed.history_length)
                    reply = {"result": task}
                elif method == "CancelTask":
                    parsed = parse_request(params, CancelTaskRequest)
                    task = await ctx.object_call(get_task, key=parsed.id, arg=None)
                    if task is None:
                        raise TaskNotFoundError()
                    if ParseDict(task, Task()).status.state in TERMINAL_STATES:
                        raise TaskNotCancelableError()
                    invocation_id = await ctx.object_call(
                        get_invocation_id, key=parsed.id, arg=None
                    )
                    if invocation_id:
                        ctx.cancel_invocation(invocation_id)
                        try:
                            await ctx.attach_invocation(invocation_id)
                        except restate.TerminalError as error:
                            if error.status_code != 409:
                                raise
                    reply = await ctx.object_call(cancel_task, key=parsed.id, arg=None)
                elif method in PUSH_METHODS:
                    raise PushNotificationNotSupportedError()
                elif method == "GetExtendedAgentCard":
                    raise ExtendedAgentCardNotConfiguredError()
                elif method in {"SendStreamingMessage", "SubscribeToTask", "ListTasks"}:
                    raise UnsupportedOperationError()
                else:
                    raise MethodNotFoundError()
            except A2AError as error:
                reply = error_reply(error)
            return {"jsonrpc": "2.0", "id": request_id, **reply}
