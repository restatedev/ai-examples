import restate
import json
import logging

from google.adk.agents.llm_agent import Agent
from google.adk.tools.tool_context import ToolContext
from google.genai import types as genai_types

from app.common.a2a.models import A2AAgent, AgentInvokeResult
from app.common.adk.middleware import durable_model_calls
from app.common.adk.restate_runner import RestateRunner
from app.common.adk.restate_session_service import RestateSessionService
from app.common.adk.restate_tools import restate_tools
from app.reimbursement.utils import ReimbursementRequest, Reimbursement, FormData, backoffice_submit_request, \
    backoffice_email_employee, end_of_month, handle_payment

logger = logging.getLogger(__name__)

APP_NAME = "agent_app"


# TOOLS


async def create_request_form(
    tool_context: ToolContext, req: ReimbursementRequest
) -> Reimbursement:
    """
    Create a request form for the employee to fill out.

    Args:
        req (ReimbursementRequest): The reimbursement request object.

    Returns:
        dict[str, Any]: A dictionary containing the request form data.
    """
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


async def return_form(tool_context: ToolContext, req: FormData) -> str:
    """
    Returns a structured json object indicating a form to complete.

    Args:
        req (FormData): The request form data

    Returns:
        dict[str, Any]: A JSON dictionary for the form response.
    """
    form_dict = {
        "type": "form",
        "form": Reimbursement.model_json_schema(),
        "form_data": req.form_request.model_dump_json(),
        "instructions": req.instructions,
    }
    return json.dumps(form_dict)


async def reimburse(
    tool_context: ToolContext, req: Reimbursement
) -> dict[str, str]:
    """
    Reimbursement workflow

    Args:
        req (Reimbursement): The reimbursement request object.
    """
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

    reimbursement_agent = Agent(
        model=durable_model_calls(restate_context, 'gemini-2.5-flash'),
        name="ReimbursementAgent",
        description=(
            "This agent handles the reimbursement process for the employees"
            " given the amount and purpose of the reimbursement."
        ),
        instruction="""
        You are an agent who handles the reimbursement process for employees.

        When you receive an reimbursement request, you should first create a new request form using create_request_form(). Only provide default values if they are provided by the user, otherwise use an empty string as the default value.
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


        For valid reimbursement requests, you can then use reimburse() to request a review of the request.
          * In your response, you should include the request_id and the status of the reimbursement request.

        """,
        tools=restate_tools(create_request_form, reimburse, return_form),
    )


    session_service = RestateSessionService(restate_context)
    await session_service.create_session(
        app_name=APP_NAME, user_id=user_id, session_id=restate_context.key()
    )

    runner = RestateRunner(
        restate_context=restate_context,
        agent=reimbursement_agent,
        app_name=APP_NAME,
        session_service=session_service
    )

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
