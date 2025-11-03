# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Academic_Research: Research advice, related literature finding, research area proposals, web knowledge access."""
import restate
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.agent_tool import AgentTool
from pydantic import BaseModel
from google.genai import types as genai_types

from middleware.middleware import durable_model_calls
from middleware.restate_runner import RestateRunner
from middleware.restate_session_service import RestateSessionService
from . import prompt
from .prompt import ACADEMIC_COORDINATOR_PROMPT
from .sub_agents.academic_newresearch import academic_newresearch_agent
from .sub_agents.academic_websearch import academic_websearch_agent

MODEL = LiteLlm(model="openai/gpt-4o")


academic_coordinator_service = restate.VirtualObject("AcademicCoordinator")


@academic_coordinator_service.handler()
async def run(ctx: restate.ObjectContext, msg: str) -> str:
    user_id = "test_user"

    academic_coordinator = LlmAgent(
        name="academic_coordinator",
        model=durable_model_calls(ctx, MODEL),
        description=(
            "analyzing seminal papers provided by the users, "
            "providing research advice, locating current papers "
            "relevant to the seminal paper, generating suggestions "
            "for new research directions, and accessing web resources "
            "to acquire knowledge"
        ),
        instruction=prompt.ACADEMIC_COORDINATOR_PROMPT,
        output_key="seminal_paper",
        tools=[
            AgentTool(agent=academic_websearch_agent),
            AgentTool(agent=academic_newresearch_agent),
        ],
    )

    session_service = RestateSessionService(ctx)
    await session_service.create_session(
        app_name=APP_NAME, user_id=user_id, session_id=ctx.key()
    )

    runner = RestateRunner(restate_context=ctx, agent=academic_coordinator, app_name=APP_NAME, session_service=session_service)

    events = runner.run_async(
        user_id=user_id,
        session_id=ctx.key(),
        new_message=genai_types.Content(
            role="user",
            parts=[genai_types.Part.from_text(text=prompt.msg)]
        )
    )

    final_response = ""
    async for event in events:
        if event.is_final_response() and event.content and event.content.parts:
            final_response = event.content.parts[0].text

    return final_response
