import restate
import json

from typing import Any, Optional
from google.adk import Runner
from google.adk.tools.tool_context import ToolContext
from google.adk.agents.llm_agent import Agent
from google.adk.apps import App
from google.genai.types import Content, Part

from app.common.a2a.models import A2AAgent, AgentInvokeResult
from app.common.adk.restate_plugin import RestatePlugin
from app.common.adk.restate_session_service import RestateSessionService
from app.common.adk.restate_utils import restate_overrides
from app.reimbursement.prompt import PROMPT
from app.reimbursement.utils import Reimbursement, backoffice_submit_request, \
    backoffice_email_employee, end_of_month, handle_payment

APP_NAME = "agents"


async def create_request_form(
    tool_context: ToolContext,
    date: Optional[str] = None,
    amount: Optional[str] = None,
    purpose: Optional[str] = None,
) -> dict[str, Any]:
    """Create a request form for the employee to fill out."""
    restate_context: restate.ObjectContext = tool_context.session.state["restate_context"]
    return {
        'request_id': str(restate_context.uuid()),
        'date': '<transaction date>' if not date else date,
        'amount': '<transaction dollar amount>' if not amount else amount,
        'purpose': '<business justification/purpose of the transaction>'
        if not purpose
        else purpose,
    }


async def return_form(
    form_request: dict[str, Any],
    instructions: Optional[str] = None,
) -> str:
    """Returns a structured json object indicating a form to complete."""
    return json.dumps({
        "type": "form",
        "form": Reimbursement.model_json_schema(),
        "form_data": form_request,
        "instructions": instructions,
    })


async def reimburse(
    tool_context: ToolContext,
    request_id: str,
    date: str,
    amount: float,
    purpose: str
) -> dict[str, str]:
    """Reimbursement workflow."""
    restate_context = tool_context.session.state["restate_context"]

    # 1. Wait for approval
    if amount > 100.0:
        # Human approval
        callback_id, callback_promise = restate_context.awakeable()
        await restate_context.run_typed(
            "Request approval", backoffice_submit_request, request_id=request_id, callback_id=callback_id
        )
        approved = await callback_promise
    else:
        # Auto-approval
        approved = True

    # 2. Notify employee
    await restate_context.run_typed("Notify", backoffice_email_employee, request_id=request_id, approved=approved)

    if not approved:
        return {"status": "rejected"}

    # 3. Schedule task for later: reimburse at end of month
    delay = end_of_month(await restate_context.time())
    restate_context.service_send(handle_payment, arg=Reimbursement(request_id=request_id, date=date, amount=amount, purpose=purpose), send_delay=delay)
    return {"status": "approved"}


# AGENTS
agent = Agent(
    model='gemini-2.5-flash',
    name="ReimbursementAgent",
    description=(
        "This agent handles the reimbursement process for the employees"
        " given the amount and purpose of the reimbursement."
    ),
    instruction=PROMPT,
    tools=[create_request_form, reimburse, return_form],
)
app = App(name=APP_NAME, root_agent=agent, plugins=[RestatePlugin()])
session_service = RestateSessionService()

reimbursement_service = restate.VirtualObject("ReimbursementService")


@reimbursement_service.handler()
async def invoke(ctx: restate.ObjectContext, query: str) -> AgentInvokeResult:
    user_id = "test_user"
    with restate_overrides(ctx):
        await session_service.create_session(
            app_name=APP_NAME, user_id=user_id, session_id=ctx.key()
        )
        runner = Runner(app=app, session_service=session_service)
        events = runner.run_async(
            user_id=user_id,
            session_id=ctx.key(),
            new_message=Content(role="user", parts=[Part.from_text(text=query)])
        )

        final_output = ""
        async for event in events:
            if event.is_final_response() and event.content and event.content.parts:
                if event.content.parts[0].text:
                    final_output = event.content.parts[0].text

        # Prepare the response
        parts = [{"type": "text", "text": final_output}]
        requires_input = "MISSING_INFO:" in final_output
        completed = not requires_input
        return AgentInvokeResult(
            parts=parts,
            require_user_input=requires_input,
            is_task_complete=completed,
        )


class ReimbursementAgent(A2AAgent):
    async def invoke(
        self, restate_context: restate.ObjectContext, query: str, session_id: str
    ) -> AgentInvokeResult:
        return await restate_context.object_call(invoke, key=session_id, arg=query)
