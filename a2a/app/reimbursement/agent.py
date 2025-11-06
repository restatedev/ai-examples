import restate
import json

from google.adk.agents.llm_agent import Agent
from google.adk.tools.tool_context import ToolContext
from google.genai import types as genai_types

from app.common.a2a.models import A2AAgent, AgentInvokeResult
from app.common.adk.middleware import durable_model_calls
from app.common.adk.restate_runner import create_restate_runner
from app.common.adk.restate_tools import restate_tools
from app.reimbursement.prompt import PROMPT
from app.reimbursement.utils import ReimbursementRequest, Reimbursement, FormData, backoffice_submit_request, \
    backoffice_email_employee, end_of_month, handle_payment

APP_NAME = "agent_app"


async def create_request_form(
    tool_context: ToolContext, req: ReimbursementRequest
) -> Reimbursement:
    """Create a request form for the employee to fill out."""
    restate_context: restate.ObjectContext = tool_context.session.state["restate_context"]
    return Reimbursement(
        request_id=str(restate_context.uuid()),
        date="<transaction date>" if not req.date else req.date,
        amount=0.0 if not req.amount else req.amount,
        purpose=(
            "<business justification/purpose of the transaction>"
            if not req.purpose
            else req.purpose
        ),
    )


async def return_form(req: FormData) -> str:
    """Returns a structured json object indicating a form to complete."""
    return json.dumps({
        "type": "form",
        "form": Reimbursement.model_json_schema(),
        "form_data": req.form_request.model_dump_json(),
        "instructions": req.instructions,
    })


async def reimburse(
    tool_context: ToolContext, req: Reimbursement
) -> dict[str, str]:
    """Reimbursement workflow."""
    restate_context: restate.ObjectContext = tool_context.session.state["restate_context"]

    # 1. Wait for approval
    if req.amount > 100.0:
        # Human approval
        callback_id, callback_promise = restate_context.awakeable()
        await restate_context.run(
            "Request approval", backoffice_submit_request, args=(req, callback_id)
        )
        approved = await callback_promise
    else:
        # Auto-approval
        approved = True

    # 2. Notify employee
    await restate_context.run("Notify", backoffice_email_employee, args=(req, approved))

    if not approved:
        return {"status": "rejected"}

    # 3. Schedule task for later: reimburse at end of month
    delay = end_of_month(await restate_context.time())
    restate_context.service_send(handle_payment, arg=req, send_delay=delay)
    return {"status": "approved"}


# AGENTS

reimbursement_service = restate.VirtualObject("ReimbursementService")


@reimbursement_service.handler()
async def invoke(restate_context: restate.ObjectContext, query: str) -> AgentInvokeResult:
    user_id = "test_user"

    agent = Agent(
        model=durable_model_calls(restate_context, 'gemini-2.5-flash'),
        name="ReimbursementAgent",
        description=(
            "This agent handles the reimbursement process for the employees"
            " given the amount and purpose of the reimbursement."
        ),
        instruction=PROMPT,
        tools=restate_tools(create_request_form, reimburse, return_form),
    )

    runner = await create_restate_runner(restate_context, APP_NAME, user_id, agent)
    events = runner.run_async(
        user_id=user_id,
        session_id=restate_context.key(),
        new_message=genai_types.Content(
            role="user",
            parts=[genai_types.Part.from_text(text=query)]
        )
    )

    final_output = ""
    async for event in events:
        if event.is_final_response() and event.content and event.content.parts:
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
