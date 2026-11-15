"""Deterministic worker for real Restate integration tests; no LLM calls."""

import asyncio
import json
import os
from datetime import timedelta
from pathlib import Path
from typing import AsyncGenerator

import hypercorn.asyncio
import restate
from a2a.types import AgentCapabilities, AgentCard, AgentInterface, AgentSkill
from fastapi import FastAPI
from google.adk import Runner
from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types

from app.common.a2a.a2a_middleware import RestateA2AMiddleware
from app.common.a2a.models import A2AAgent, AgentInvokeResult
from app.common.adk.restate_plugin import RestatePlugin
from app.common.adk.restate_session_service import RestateSessionService
from app.common.adk.restate_utils import current_restate_context, restate_overrides


def record(kind: str, stage: str, session: str, **values: str) -> str:
    with Path(os.environ["PROBE_EVENTS"]).open("a") as stream:
        stream.write(
            json.dumps(
                {
                    "kind": kind,
                    "stage": stage,
                    "session": session,
                    "pid": os.getpid(),
                    **values,
                }
            )
            + "\n"
        )
        stream.flush()
        os.fsync(stream.fileno())
    return stage


def fail() -> None:
    raise restate.TerminalError("Deliberate terminal failure")


def conflict() -> None:
    raise restate.TerminalError("Business conflict", status_code=409)


class DeterministicModel(BaseLlm):
    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:
        record("model", "response", current_restate_context().key())
        yield LlmResponse(
            content=types.Content(
                role="model", parts=[types.Part(text="local ADK response")]
            )
        )


adk_app = App(
    name="recovery_probe",
    root_agent=Agent(name="probe", model=DeterministicModel(model="deterministic")),
    plugins=[RestatePlugin()],
)
session_service = RestateSessionService()


class ProbeAgent(A2AAgent):
    async def invoke(
        self, ctx: restate.ObjectContext, query: str, session_id: str
    ) -> AgentInvokeResult:
        if query == "adk":
            with restate_overrides(ctx):
                await session_service.create_session(
                    app_name=adk_app.name, user_id="test", session_id=session_id
                )
                runner = Runner(app=adk_app, session_service=session_service)
                final = ""
                async for event in runner.run_async(
                    user_id="test",
                    session_id=session_id,
                    new_message=types.Content(
                        role="user", parts=[types.Part(text="hello")]
                    ),
                ):
                    if (
                        event.is_final_response()
                        and event.content
                        and event.content.parts
                    ):
                        final = event.content.parts[0].text or ""
            record("adk-checkpoint", "model-saved", session_id)
            await ctx.sleep(timedelta(seconds=8))
            return AgentInvokeResult(parts=[{"text": final}])
        if query == "need-input":
            return AgentInvokeResult(
                parts=[{"text": "Please provide input"}], require_user_input=True
            )
        if query == "fail":
            await ctx.run_typed("terminal failure", fail)
        if query == "conflict":
            await ctx.run_typed("business conflict", conflict)
        await ctx.run_typed(
            "first step", record, kind="effect", stage="first", session=session_id
        )
        # Seeing this marker means the run future resolved after journaling.
        record("checkpoint", "first-saved", session_id)
        if query == "slow":
            await ctx.sleep(timedelta(seconds=8))
        elif query == "approval":
            callback_id, promise = ctx.awakeable()
            await ctx.run_typed(
                "request approval",
                record,
                kind="approval",
                stage="waiting",
                session=session_id,
                callback_id=callback_id,
            )
            record(
                "approval-checkpoint",
                "approval-saved",
                session_id,
                callback_id=callback_id,
            )
            await promise
        await ctx.run_typed(
            "second step", record, kind="effect", stage="second", session=session_id
        )
        return AgentInvokeResult(parts=[{"text": f"done: {query}"}])


middleware = RestateA2AMiddleware(
    AgentCard(
        name="RecoveryProbe",
        description="Deterministic recovery probe",
        version="1",
        supported_interfaces=[
            AgentInterface(
                url="http://127.0.0.1:8080",
                protocol_binding="JSONRPC",
                protocol_version="1.0",
            )
        ],
        capabilities=AgentCapabilities(),
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain"],
        skills=[
            AgentSkill(
                id="probe", name="Probe", description="Probe recovery", tags=["test"]
            )
        ],
    ),
    ProbeAgent(),
)
app = FastAPI()


@app.get("/health")
async def health() -> dict:
    return {"pid": os.getpid()}


@app.get("/.well-known/agent-card.json")
async def card() -> dict:
    return middleware.agent_card_json


app.mount("/restate/v1", restate.app(list(middleware)))

if __name__ == "__main__":
    config = hypercorn.Config()
    config.bind = ["127.0.0.1:19080"]
    asyncio.run(hypercorn.asyncio.serve(app, config))
