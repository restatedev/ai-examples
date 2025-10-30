import json
import logging
import os
import uuid

import restate
import httpx

from agents import function_tool, RunContextWrapper

from a2a.types import (
    AgentCard,
    SendTaskRequest,
    TaskSendParams,
    Message,
    TextPart,
    Task,
    TaskState,
    JSONRPCRequest,
    SendTaskResponse,
)
from a2a_samples.common.openai.middleware import raise_restate_errors

logger = logging.getLogger(__name__)

REMOTE_AGENT_URLS = os.getenv("REMOTE_AGENTS", "http://localhost:9081").split(",")


def agent_as_tool(name: str, description: str, url: str):
    @function_tool(name_override=name, description_override=description, failure_error_function=raise_restate_errors)
    async def agent_tool(
        wrapper: RunContextWrapper[restate.ObjectContext], query: str
    ) -> Task | None:
        """Invoke the agent with a query."""
        return await call_remote_agent(wrapper.context, name, url=url, message=query)

    return agent_tool


def init_remote_agents():
    remote_agents = []
    for remote_agent_url in REMOTE_AGENT_URLS:
        logger.info(f"Loading remote agent from {remote_agent_url}")
        resp = httpx.get(f"{remote_agent_url}/.well-known/agent.json")
        resp.raise_for_status()
        agent_card = AgentCard(**resp.json())
        remote_agents.append(
            agent_as_tool(agent_card.name, agent_card.description, agent_card.url)
        )
    return remote_agents


async def call_remote_agent(
    ctx: restate.ObjectContext, name: str, url: str, message: str
) -> Task | None:
    request = await ctx.run_typed(
        "Generate send request",
        lambda: SendTaskRequest(
            id=uuid.uuid4().hex,
            params=TaskSendParams(
                id=uuid.uuid4().hex,
                sessionId=ctx.key(),
                message=Message(message_id=str(ctx.uuid()), role="user", parts=[TextPart(text=message)]),
            ),
        ),
    )
    logger.info(
        f"Sending request to {name} at {url} with request payload: {request.model_dump()}"
    )
    response = await ctx.run_typed("Call Agent", send_request, url=url, request=request)
    logger.info(f"Received response from {name}: {response.result.model_dump_json()}")

    match response.result.status.state:
        case TaskState.INPUT_REQUIRED:
            final_output = f"MISSING_INFO: {response.result.status.message.parts}"
        case TaskState.COMPLETED:
            final_output = response.result.artifacts
        case TaskState.CANCELED:
            final_output = "Task canceled"
        case TaskState.FAILED:
            final_output = f"Task failed: {response.error.message}"
        case TaskState.SUBMITTED:
            final_output = "Task submitted"
        case TaskState.WORKING:
            final_output = "Task is in progress"
        case _:
            final_output = "Task status unknown"

    return final_output


async def send_request(url: str, request: JSONRPCRequest) -> SendTaskResponse:
    async with httpx.AsyncClient() as client:
        # retry any errors that come out of this
        resp = await client.post(
            url,
            json=request.model_dump(),
            headers={"idempotency-key": request.id},
            timeout=300,
        )
        resp.raise_for_status()

        try:
            return SendTaskResponse(**resp.json())
        except (json.JSONDecodeError, TypeError) as e:
            # feed error message back to LLM
            raise Exception(
                f"Response was not in A2A SendTaskResponse format. Error: {str(e)}"
            ) from e
