import logging
import uuid
from abc import ABC, abstractmethod

import httpx
from pydantic import BaseModel

from .agent_session import AgentInput, AgentResponse, Agent, run_agent_session
import restate
from datetime import datetime
from restate.serde import PydanticJsonSerde
from typing import Union, AsyncIterable, List, Any

from common.types import (
    SendTaskRequest,
    TaskSendParams,
    TaskStatus,
    Artifact,
    TextPart,
    TaskState,
    Task,
    SendTaskResponse,
    JSONRPCResponse,
    SendTaskStreamingRequest,
    SendTaskStreamingResponse,
    AgentCard,
    A2ARequest,
    GetTaskRequest,
    CancelTaskRequest,
    SetTaskPushNotificationRequest,
    GetTaskPushNotificationRequest,
    TaskResubscriptionRequest,
    GetTaskPushNotificationResponse,
    SetTaskPushNotificationResponse,
    CancelTaskResponse,
    GetTaskResponse,
    TaskNotFoundError,
    TaskQueryParams,
    TaskIdParams,
    TaskPushNotificationConfig,
    InternalError,
    PushNotificationConfig,
    JSONRPCError,
    JSONRPCRequest,
    AgentInvokeResult,
    Message,
)

logger = logging.getLogger(__name__)

# K/V stored in Restate
TASK = "task"
INVOCATION_ID = "invocation-id"
PUSH_NOTIFICATION_INFO = "push-notification-info"


class GenericAgent(ABC):

    async def invoke_with_context(
        self, ctx: restate.ObjectContext, query: str, session_id: str
    ) -> AgentInvokeResult:
        """
        Invoke the agent with a context.
        """
        return await ctx.run(
            "Agent invoke",
            lambda: self.invoke(
                query=query,
                session_id=session_id,
            ),
            type_hint=AgentInvokeResult,
        )

    @abstractmethod
    def invoke(self, query: str, session_id: str) -> AgentInvokeResult:
        pass


class GenericRestateAgent(ABC):
    def __init__(self, starting_agent: Agent, agents: list[Agent]):
        super().__init__()
        self.starting_agent = starting_agent
        self.agents = agents

    async def invoke_with_context(
        self, ctx: restate.ObjectContext, query: str, session_id: str
    ) -> AgentInvokeResult:

        agent_input = AgentInput(
            starting_agent=self.starting_agent, agents=self.agents, message=query
        )

        agent_response: AgentResponse = await run_agent_session(ctx, agent_input)
        result = agent_response.final_output

        parts = [{"type": "text", "text": result}]
        requires_input = "MISSING_INFO:" in result
        completed = not requires_input
        return AgentInvokeResult(
            parts=parts,
            require_user_input=requires_input,
            is_task_complete=completed,
        )


def a2a_services(
    agent_name: str,
    agent_card: AgentCard,
    agent: Union[GenericAgent, GenericRestateAgent],
) -> list[Union[restate.Service, restate.VirtualObject]]:
    """
    Creates an A2A server for reimbursement processing with customizable name and description.

    Args:
        agent_name: Name of the A2A server
        agent_card: AgentCard object containing agent information
        agent: Agent object that implements the invoke method

    Returns:
        A configured restate Service instance
    """
    a2a_server = restate.Service(f"{agent_name}A2AServer", agent_card.description)

    @a2a_server.handler()
    async def get_agent_card(ctx: restate.Context) -> AgentCard:
        return agent_card

    @a2a_server.handler()
    async def process_request(
        ctx: restate.Context, req: JSONRPCRequest
    ) -> JSONRPCResponse:
        try:
            json_rpc_request = A2ARequest.validate_python(req.model_dump())

            if isinstance(json_rpc_request, GetTaskRequest):
                result = await on_get_task(ctx, json_rpc_request)
            elif isinstance(json_rpc_request, SendTaskRequest):
                result = await ctx.object_call(
                    handle_send_task_request,
                    key=json_rpc_request.params.id,
                    arg=json_rpc_request,
                    idempotency_key=str(json_rpc_request.id),
                )
            elif isinstance(json_rpc_request, CancelTaskRequest):
                result = await on_cancel_task(ctx, json_rpc_request)
            elif isinstance(json_rpc_request, SendTaskStreamingRequest):
                result = await on_send_task_subscribe(ctx, json_rpc_request)
            elif isinstance(json_rpc_request, SetTaskPushNotificationRequest):
                result = await on_set_task_push_notification(ctx, json_rpc_request)
            elif isinstance(json_rpc_request, GetTaskPushNotificationRequest):
                result = await on_get_task_push_notification(ctx, json_rpc_request)
            elif isinstance(json_rpc_request, TaskResubscriptionRequest):
                result = await on_resubscribe_to_task(ctx, json_rpc_request)
            else:
                raise restate.exceptions.TerminalError(
                    status_code=500,
                    message=f"Unexpected request type: {json_rpc_request.method}",
                )

            logger.info(
                f"Processed request: {json_rpc_request.method} => {result.model_dump_json(exclude_none=True)}"
            )
            return result
        except restate.exceptions.TerminalError as e:
            logger.error(f"Error processing request: {e}")
            return JSONRPCResponse(
                id=req.id,
                error=JSONRPCError(code=e.status_code, message=e.message),
            )

    async def on_get_task(
        ctx: restate.Context, request: GetTaskRequest
    ) -> GetTaskResponse:
        # Implementation of https://google.github.io/A2A/#/documentation?id=get-a-task
        logger.info(f"Getting task {request.params.id}")
        task_query_params: TaskQueryParams = request.params

        task = await ctx.object_call(get_task, key=task_query_params.id, arg=None)
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

    async def on_cancel_task(
        ctx: restate.Context, request: CancelTaskRequest
    ) -> CancelTaskResponse:
        # Implementation of https://google.github.io/A2A/#/documentation?id=cancel-a-task
        logger.info(f"Cancelling task {request.params.id}")
        task_id_params: TaskIdParams = request.params

        task = await ctx.object_call(get_task, key=task_id_params.id, arg=None)
        if task is None:
            return CancelTaskResponse(id=request.id, error=TaskNotFoundError())
        invocation_id = await ctx.object_call(
            get_invocation_id, key=task_id_params.id, arg=None
        )
        if invocation_id is None:
            # Task either doesn't exist or is already completed
            return await ctx.object_call(
                cancel_task, key=task_id_params.id, arg=request
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

    async def on_set_task_push_notification(
        ctx: restate.Context, request: SetTaskPushNotificationRequest
    ) -> SetTaskPushNotificationResponse:
        logger.info(f"Setting task push notification {request.params.id}")
        task_notification_params: TaskPushNotificationConfig = request.params

        task = await ctx.object_call(
            get_task, key=task_notification_params.id, arg=None
        )
        if task is None:
            return JSONRPCResponse(
                id=request.id,
                error=InternalError(
                    message="An error occurred while setting push notification info"
                ),
            )

        await ctx.object_call(
            set_push_notification_info,
            key=task_notification_params.id,
            arg=task_notification_params.pushNotificationConfig,
        )
        return SetTaskPushNotificationResponse(
            id=request.id, result=task_notification_params
        )

    async def on_get_task_push_notification(
        ctx: restate.Context, request: GetTaskPushNotificationRequest
    ) -> GetTaskPushNotificationResponse:
        task_params: TaskIdParams = request.params
        logger.info(f"Getting task push notification {task_params.id}")

        task = await ctx.object_call(get_task, key=task_params.id, arg=None)
        if task is None:
            return GetTaskPushNotificationResponse(
                id=request.id,
                error=InternalError(
                    message="An error occurred while getting push notification info"
                ),
            )

        push_notification = await ctx.object_call(
            get_push_notification_info, key=task_params.id, arg=None
        )
        result = (
            TaskPushNotificationConfig(
                id=task_params.id, pushNotificationConfig=push_notification.config
            )
            if push_notification.config
            else None
        )
        return GetTaskPushNotificationResponse(id=request.id, result=result)

    task_object = restate.VirtualObject(f"{agent_name}TaskObject")

    @task_object.handler(kind="shared")
    async def get_invocation_id(
        ctx: restate.ObjectSharedContext,
    ) -> str | None:
        task_id = ctx.key()
        logger.info(f"Getting invocation id for task {task_id}")
        return await ctx.get(INVOCATION_ID) or None

    @task_object.handler(output_serde=PydanticJsonSerde(Task), kind="shared")
    async def get_task(
        ctx: restate.ObjectSharedContext,
    ) -> Task | None:
        task_id = ctx.key()
        logger.info(f"Getting task {task_id}")
        return await ctx.get(TASK, type_hint=Task) or None

    @task_object.handler()
    async def handle_send_task_request(
        ctx: restate.ObjectContext, request: SendTaskRequest
    ) -> SendTaskResponse:
        # Implementation of https://google.github.io/A2A/#/documentation?id=send-a-task
        logger.info(
            "Starting task execution workflow %s for task %s",
            request.id,
            request.params.id,
        )

        task_send_params: TaskSendParams = request.params
        if not task_send_params.sessionId:
            session_id = await ctx.run(
                "Generate session id", lambda: str(uuid.uuid4().hex)
            )
            task_send_params.sessionId = session_id

        # Store this invocation ID so it can be cancelled by someone else
        await set_invocation_id(ctx, ctx.request().id)

        # Persist the request data
        await upsert_task(ctx, task_send_params)

        try:
            # Forward the request to the agent
            result = await agent.invoke_with_context(
                ctx,
                query=_get_user_query(task_send_params),
                session_id=task_send_params.sessionId,
            )

            if result.require_user_input:
                updated_task = await update_store(
                    ctx,
                    state=TaskState.INPUT_REQUIRED,
                    status_message=Message(role="agent", parts=result.parts),
                )
            else:
                updated_task = await update_store(
                    ctx,
                    state=TaskState.COMPLETED,
                    artifacts=[Artifact(parts=result.parts)],
                )

            ctx.clear(INVOCATION_ID)
            return SendTaskResponse(id=request.id, result=updated_task)
        except restate.exceptions.TerminalError as e:
            if e.status_code == 409 and e.message == "cancelled":
                logger.info(f"Task {task_send_params.id} was cancelled")
                cancelled_task = await update_store(ctx, state=TaskState.CANCELED)
                ctx.clear(INVOCATION_ID)
                return SendTaskResponse(id=request.id, result=cancelled_task)
            else:
                logger.error(f"Error while processing task {task_send_params.id}: {e}")
                failed_task = await update_store(ctx, state=TaskState.FAILED)
                ctx.clear(INVOCATION_ID)
                return SendTaskResponse(id=request.id, result=failed_task)

    # Gets called for tasks with no ongoing invocations
    # e.g. waiting for user input
    @task_object.handler()
    async def cancel_task(
        ctx: restate.ObjectContext, request: CancelTaskRequest
    ) -> CancelTaskResponse:
        cancelled_task = await update_store(ctx, state=TaskState.CANCELED)
        return CancelTaskResponse(id=request.id, result=cancelled_task)

    if isinstance(agent, GenericAgent):
        return [a2a_server, task_object]
    elif isinstance(agent, GenericRestateAgent):
        return [a2a_server, task_object]


async def on_send_task_subscribe(
    ctx: restate.Context, request: SendTaskStreamingRequest
) -> Union[AsyncIterable[SendTaskStreamingResponse], JSONRPCResponse]:
    raise restate.exceptions.TerminalError(f"Not implemented: {request.method}")


async def on_resubscribe_to_task(
    ctx: restate.Context, request: TaskResubscriptionRequest
) -> Union[AsyncIterable[SendTaskResponse], JSONRPCResponse]:
    raise restate.exceptions.TerminalError(
        status_code=500, message=f"Not implemented: {request.method}"
    )


def _get_user_query(task_send_params: TaskSendParams) -> str:
    part = task_send_params.message.parts[0]
    if not isinstance(part, TextPart):
        raise restate.exceptions.TerminalError("Only text parts are supported")
    return part.text


async def send_task_notification(self, ctx: restate.Context, task: Task):
    push_info = await ctx.object_call(get_push_notification_info, key=task.id, arg=None)
    if not push_info:
        logger.info(f"No push notification info found for task {task.id}")
        return

    logger.info(f"Notifying for task {task.id} => {task.status.state}")

    # TODO we ignore authentication for now
    # will keep retrying until it succeeds
    def send_notification() -> dict[str, Any]:
        response = httpx.post(push_info.url, json=task.model_dump(exclude_none=True))
        response.raise_for_status()
        return response.json()

    await ctx.run("Push notification", send_notification)
    logger.info(f"Push-notification sent for URL: {push_info.url}")


async def set_invocation_id(ctx: restate.ObjectContext, invocation_id: str):
    task_id = ctx.key()
    logger.info(f"Adding invocation id {invocation_id} for task {task_id}")
    current_invocation_id = await ctx.get(INVOCATION_ID)
    if current_invocation_id is not None:
        raise restate.exceptions.TerminalError(
            "There is an ongoing invocation. How did we end up here?"
        )
    ctx.set(INVOCATION_ID, invocation_id)


async def upsert_task(
    ctx: restate.ObjectContext, task_send_params: TaskSendParams
) -> Task:
    task_id = ctx.key()
    logger.info(f"Upserting task {task_id}")

    task_state = await ctx.get(TASK, type_hint=Task)
    if task_state is None:
        task_state = await ctx.run(
            "Create task",
            lambda run_params=task_send_params: Task(
                id=run_params.id,
                sessionId=run_params.sessionId,
                status=TaskStatus(state=TaskState.SUBMITTED, timestamp=datetime.now()),
                history=[run_params.message] if run_params.message else [],
            ),
            type_hint=Task,
        )
    else:
        task_state.history.append(task_send_params.message)

    ctx.set(TASK, task_state)
    return task_state


async def update_store(
    ctx: restate.ObjectContext,
    state: TaskState | None,
    status_message: Message | None = None,
    artifacts: List[Artifact] | None = None,
) -> Task:
    task_id = ctx.key()
    logger.info(f"Updating status task {task_id} to {state}")

    task = await ctx.get(TASK, type_hint=Task)
    if task is None:
        logger.error("Task %s not found for updating the task", task_id)
        raise restate.exceptions.TerminalError(f"Task {task_id} not found")

    new_task_status = await ctx.run(
        "task status",
        lambda task_state=state: TaskStatus(
            state=task_state, timestamp=datetime.now(), message=status_message
        ),
        type_hint=TaskStatus,
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


push_notification_manager = restate.VirtualObject("PushNotificationManager")


class OptionalPushNotificationConfig(BaseModel):
    config: PushNotificationConfig | None = None


@push_notification_manager.handler(kind="shared")
async def get_push_notification_info(
    ctx: restate.ObjectSharedContext,
) -> OptionalPushNotificationConfig:
    task_id = ctx.key()
    logger.info(f"Getting push notifications task {task_id}")
    return OptionalPushNotificationConfig(
        config=await ctx.get(PUSH_NOTIFICATION_INFO, type_hint=PushNotificationConfig)
    )


@push_notification_manager.handler()
async def set_push_notification_info(
    ctx: restate.ObjectContext, notification_config: PushNotificationConfig
):
    task_id = ctx.key()
    logger.info(f"Setting push notifications task {task_id}")
    ctx.set(PUSH_NOTIFICATION_INFO, notification_config)
