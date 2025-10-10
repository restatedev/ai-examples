import restate
import random
import calendar
import json
import logging

from typing import Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, ConfigDict

from agents import Agent, function_tool, Runner, RunConfig, RunContextWrapper, ModelSettings

from a2a.common.a2a.models import A2AAgent, AgentInvokeResult
from a2a.common.openai.middleware import DurableModelCalls, raise_restate_errors

logger = logging.getLogger(__name__)


class ReimbursementRequest(BaseModel):
    """
    A request for reimbursement.

    Args:
        date (Optional[str]): The date of the request. Or None.
        amount (Optional[str]): The requested amount. Or None.
        purpose (Optional[str]): The purpose of the request. Or None.
    """

    date: Optional[str] = None
    amount: Optional[float] = None
    purpose: Optional[str] = None


class Reimbursement(BaseModel):
    """
    A request for reimbursement.

    Args:
        request_id (str): The ID of the request.
        date (str): The date of the request.
        amount (float): The requested amount in USD.
        purpose (str): The purpose of the request.
    """

    request_id: str
    date: str
    amount: float
    purpose: str


class FormData(BaseModel):
    """
    A form data object for reimbursement requests.

    Args:
        form_request (dict[str, Any]): The request form data.
        instructions (str): Instructions for processing the form. Or None.
    """

    form_request: Reimbursement
    instructions: Optional[str] = None
    model_config = ConfigDict(extra="forbid")


# TOOLS


@function_tool(failure_error_function=raise_restate_errors)
async def create_request_form(
    wrapper: RunContextWrapper[restate.ObjectContext], req: ReimbursementRequest
) -> Reimbursement:
    """
    Create a request form for the employee to fill out.

    Args:
        req (ReimbursementRequest): The reimbursement request object.

    Returns:
        dict[str, Any]: A dictionary containing the request form data.
    """
    restate_context = wrapper.context
    date, amount, purpose = req.date, req.amount, req.purpose

    request_id = await restate_context.run(
        "Assign ID", lambda: "request_id_" + str(random.randint(1000000, 9999999))
    )
    reimbursement = Reimbursement(
        request_id=request_id,
        date="<transaction date>" if not date else date,
        amount=0.0 if not amount else amount,
        purpose=(
            "<business justification/purpose of the transaction>"
            if not purpose
            else purpose
        ),
    )
    return reimbursement


@function_tool(failure_error_function=raise_restate_errors)
async def return_form(req: FormData) -> str:
    """
    Returns a structured json object indicating a form to complete.

    Args:
        req (FormData): The request form data

    Returns:
        dict[str, Any]: A JSON dictionary for the form response.
    """
    form_request, instructions = req.form_request, req.instructions

    form_dict = {
        "type": "form",
        "form": Reimbursement.model_json_schema(),
        "form_data": form_request.model_dump_json(),
        "instructions": instructions,
    }
    return json.dumps(form_dict)


@function_tool(failure_error_function=raise_restate_errors)
async def reimburse(
    wrapper: RunContextWrapper[restate.ObjectContext], req: Reimbursement
) -> dict[str, str]:
    """
    Reimbursement workflow

    Args:
        req (Reimbursement): The reimbursement request object.
    """
    restate_context = wrapper.context
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
    restate_context.service_send(handle_payment, arg=req, send_delay=end_of_month())
    return {"status": "approved"}


# AGENTS

reimbursement_agent = Agent[restate.Context](
    name="ReimbursementAgent",
    handoff_description=(
        "This agent handles the reimbursement process for the employees"
        " given the amount and purpose of the reimbursement."
    ),
    instructions="""
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
    tools=[create_request_form, reimburse, return_form],
)


reimbursement_service = restate.VirtualObject("ReimbursementService")


@reimbursement_service.handler()
async def invoke(restate_context: restate.ObjectContext, query: str) -> AgentInvokeResult:
    # Load the conversation history
    memory = await restate_context.get("memory") or []
    memory.append({"role": "user", "content": query})

    result = await Runner.run(
        reimbursement_agent,
        input=memory,
        # Pass the Restate context to tools to make tool execution steps durable
        context=restate_context,
        # Choose any model and let Restate persist your calls
        run_config=RunConfig(
            model="gpt-4o",
            model_provider=DurableModelCalls(restate_context),
            model_settings = ModelSettings(parallel_tool_calls=False),
            ),
    )
    final_output = result.final_output

    # Store the conversation history
    memory.append({"role": "assistant", "content": final_output})
    restate_context.set("memory", memory)

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


# UTILS


@reimbursement_service.handler()
async def handle_payment(ctx: restate.ObjectContext, req: Reimbursement):
    pass


def backoffice_submit_request(req: Reimbursement, id: str):
    print(
        "=" * 50,
        f"\n Requesting approval for {req.request_id} \n",
        f"Resolve via: \n"
        f"curl localhost:8080/restate/awakeables/{id}/resolve --json '{{\"approved\": true}}' \n",
        "=" * 50,
    )


def backoffice_email_employee(req: Reimbursement, approved: bool):
    logger.info("Notifying backoffice employee of reimbursement approval")


def end_of_month():
    now = datetime.now()
    last_day = calendar.monthrange(now.year, now.month)[1]
    end_of_month = datetime(now.year, now.month, last_day, 23, 59, 59, 999999)

    time_remaining = end_of_month - now
    return timedelta(seconds=time_remaining.total_seconds())
