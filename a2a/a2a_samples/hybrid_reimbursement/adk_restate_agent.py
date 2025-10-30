# pylint: disable=C0116
"""Bridge between Google ADK agents and Restate durable execution."""

import logging
from typing import Any, AsyncIterable, Dict, List

import restate
from google.adk.agents.llm_agent import LlmAgent
from google.adk.runners import Runner
from google.genai import types

from a2a_samples.common.a2a.models import A2AAgent, AgentInvokeResult
from a2a.types import Part, TextPart, DataPart


logger = logging.getLogger(__name__)


class ADKRestateAgent(A2AAgent):
    """Wrapper that makes Google ADK agents compatible with Restate."""

    def __init__(self, adk_agent: LlmAgent, runner: Runner):
        self.adk_agent = adk_agent
        self.runner = runner
        self._user_id = "restate_bridge_user"

    async def invoke(
        self, restate_context: restate.ObjectContext, query: str, session_id: str
    ) -> AgentInvokeResult:
        """Invoke Google ADK agent with Restate durability."""
        logger.info("Invoking ADK agent %s with session %s", self.adk_agent.name, session_id)

        try:
            # Ensure session exists using Restate's durable execution
            session = await restate_context.run(
                "ensure_session_exists",
                self._ensure_session_exists,
                args=(session_id,)
            )

            # Create content for ADK agent
            content = types.Content(
                role='user', parts=[types.Part.from_text(text=query)]
            )

            # Stream results from ADK agent
            final_response = None
            processing_updates = []

            async for event in self._run_adk_agent_durable(
                restate_context, session["id"], content
            ):
                if event.get('is_task_complete', False):
                    final_response = event.get('content', '')
                    break
                else:
                    processing_updates.append(event.get('updates', ''))

            # Convert ADK response to A2A format
            if isinstance(final_response, dict):
                # If response is a dict (like form data), convert to DataPart
                parts = [DataPart(data=final_response)]
                require_user_input = True
            elif isinstance(final_response, str):
                # Text response
                parts = [TextPart(text=final_response)]
                require_user_input = "MISSING_INFO:" in final_response or any(
                    form_indicator in final_response.lower()
                    for form_indicator in ["form", "required", "missing"]
                )
            else:
                # Fallback
                parts = [TextPart(text=str(final_response))]
                require_user_input = False

            return AgentInvokeResult(
                parts=parts,
                require_user_input=require_user_input,
                is_task_complete=not require_user_input,
            )

        except Exception as e:
            logger.error("Error invoking ADK agent: %s", e)
            # Return error as text response
            return AgentInvokeResult(
                parts=[TextPart(text=f"Error processing request: {str(e)}")],
                require_user_input=False,
                is_task_complete=True,
            )


    async def _run_adk_agent_durable(
        self,
        restate_context: restate.ObjectContext,
        session_id: str,
        content: types.Content,
    ) -> AsyncIterable[Dict[str, Any]]:
        """Run ADK agent with durable execution tracking."""
        try:
            # First ensure session exists with proper creation
            await restate_context.run(
                "ensure_session_exists",
                self._ensure_session_exists,
                args=(session_id,)
            )

            # Use Restate's durable execution for the ADK agent call

            async def collect_events():
                results = []
                try:
                    events = self.runner.run_async(
                        user_id=self._user_id,
                        session_id=session_id,
                        new_message=content
                    )
                    async for event in events:
                        if event.is_final_response():
                            response = ''
                            if (
                                event.content
                                and event.content.parts
                                and event.content.parts[0].text
                            ):
                                response = '\n'.join(
                                    [p.text for p in event.content.parts if p.text]
                                )
                            elif (
                                event.content
                                and event.content.parts
                                and any(
                                    [
                                        True
                                        for p in event.content.parts
                                        if p.function_response
                                    ]
                                )
                            ):
                                response = next(
                                    p.function_response.model_dump()
                                    for p in event.content.parts
                                )

                            results.append({
                                'is_task_complete': True,
                                'content': response,
                            })
                            break
                        else:
                            results.append({
                                'is_task_complete': False,
                                'updates': 'Processing...',
                            })
                except Exception as runner_error:
                    logger.error("Error in ADK runner: %s", runner_error)
                    results.append({
                        'is_task_complete': True,
                        'content': f"ADK Runner Error: {str(runner_error)}",
                    })
                return results

            # Execute the ADK agent as a durable side effect
            result_list = await restate_context.run(
                "execute_adk_agent",
                collect_events
            )

            # Yield collected results
            for result in result_list:
                yield result

        except Exception as e:
            logger.error("Error in durable ADK execution: %s", e)
            yield {
                'is_task_complete': True,
                'content': f"Error: {str(e)}",
            }

    async def _ensure_session_exists(self, session_id: str) -> Dict[str, Any]:
        """Ensure session exists in ADK session service."""
        try:
            # Try to get existing session
            session = await self.runner.session_service.get_session(
                app_name=self.adk_agent.name,
                user_id=self._user_id,
                session_id=session_id,
            )

            if session is None:
                # Create new session
                logger.info(f"Creating new ADK session: {session_id}")
                session = await self.runner.session_service.create_session(
                    app_name=self.adk_agent.name,
                    user_id=self._user_id,
                    state={},
                    session_id=session_id,
                )

            return {
                "id": session.id,
                "user_id": session.user_id,
                "app_name": session.app_name,
                "state": session.state,
            }
        except Exception as e:
            logger.error("Error ensuring session exists: %s", e)
            # Return a default session structure
            return {
                "id": session_id,
                "user_id": self._user_id,
                "app_name": self.adk_agent.name,
                "state": {},
            }


class ADKAgentFactory:
    """Factory for creating ADK agents compatible with Restate."""

    @staticmethod
    def create_reimbursement_agent() -> ADKRestateAgent:
        """Create a reimbursement agent using Google ADK with Restate integration."""
        from google.adk.agents.llm_agent import LlmAgent
        from google.adk.models.lite_llm import LiteLlm
        from google.adk.artifacts import InMemoryArtifactService
        from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
        from google.adk.runners import Runner
        from google.adk.sessions import InMemorySessionService

        # Import tool functions from ADK reimbursement example
        try:
            from a2a_samples.adk_expense_reimbursement.agent import (
                create_request_form,
                reimburse,
                return_form,
            )
        except ImportError:
            logger.warning("Could not import ADK reimbursement tools, using dummy functions")
            # Define dummy functions if import fails
            def create_request_form(**_kwargs):
                return {"request_id": "dummy", "message": "Tool not available"}

            def reimburse(**_kwargs):
                return {"status": "Tool not available"}

            def return_form(**_kwargs):
                return '{"type": "form", "message": "Tool not available"}'

        import os
        litellm_model = os.getenv('LITELLM_MODEL', 'gemini/gemini-2.0-flash-001')

        # Build the ADK agent
        agent = LlmAgent(
            model=LiteLlm(model=litellm_model),
            name='reimbursement_agent_hybrid',
            description=(
                'Hybrid agent that handles reimbursement process with Restate durability'
            ),
            instruction="""
    You are an agent who handles the reimbursement process for employees.

    When you receive a reimbursement request, you should first create a new request form using create_request_form(). Only provide default values if they are provided by the user, otherwise use an empty string as the default value.
      1. 'Date': the date of the transaction.
      2. 'Amount': the dollar amount of the transaction.
      3. 'Business Justification/Purpose': the reason for the reimbursement.

    Once you created the form, you should return the result of calling return_form with the form data from the create_request_form call.
    If you request more info from the user, always start your response with "MISSING_INFO:". This is very important, don't change this part.

    Once you received the filled-out form back from the user, you should then check the form contains all required information:
      1. 'Date': the date of the transaction.
      2. 'Amount': the value of the amount of the reimbursement being requested.
      3. 'Business Justification/Purpose': the item/object/artifact of the reimbursement.

    If you don't have all of the information, you should reject the request directly by calling the request_form method, providing the missing fields.

    For valid reimbursement requests, you can then use reimburse() to reimburse the employee.
      * In your response, you should include the request_id and the status of the reimbursement request.
    """,
            tools=[
                create_request_form,
                reimburse,
                return_form,
            ],
        )

        # Build the runner
        runner = Runner(
            app_name=agent.name,
            agent=agent,
            artifact_service=InMemoryArtifactService(),
            session_service=InMemorySessionService(),
            memory_service=InMemoryMemoryService(),
        )

        return ADKRestateAgent(agent, runner)
