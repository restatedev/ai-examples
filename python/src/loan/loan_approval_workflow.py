import datetime

import restate
from pydantic import BaseModel
from restate.serde import PydanticJsonSerde

import utils.account as account
from utils.agent_session import Agent, AgentInput
from utils.agent_session import run as agent_session_run


class LoanRequest(BaseModel):
    """
    A loan request object.

    Args:
        customer_id (str): The customer ID who requested the loan.
        loan_amount (int): The amount of the loan.
        loan_duration_months (int): The duration of the loan in months.
    """

    customer_id: str
    loan_amount: int
    loan_duration_months: int


class LoanDecision(BaseModel):
    """
    A loan decision object.

    Args:
        approved (bool): Whether the loan was approved or not.
        reason (str): The reason for the decision.
    """

    approved: bool


loan_approval_wf = restate.Workflow("LoanApprovalWorkflow")


@loan_approval_wf.main()
async def run(ctx: restate.WorkflowContext, loan_request: LoanRequest) -> LoanDecision:
    """
    Run the loan approval workflow.

    Args:
        loan_request (LoanRequest): The loan request object.
    """
    import my_agents
    ctx.set("status", "Submitted")

    # 1. Gather extra info on the customer
    credit_score = await ctx.object_call(
        account.calculate_credit_score, key=loan_request.customer_id, arg=None
    )

    transaction_history = await ctx.object_call(
        account.get_transaction_history, key=loan_request.customer_id, arg=None
    )

    # 2. Run the loan approval process
    if loan_request.loan_amount < 1000000:
        # Loans under 1M can be approved by the AI agent
        ctx.set("status", "Running AI-based assessment")
        await invoke_agent(
            ctx,
            my_agents.loan_assessment_agent,
            f"Review the loan request: {loan_request.model_dump_json()};"
            f"credit score:{credit_score};"
            f"transaction history: {transaction_history.model_dump_json()};"
            "Ask the customer for more information if needed",
        )
        approved = await ctx.promise(
            "agent_loan_review", serde=PydanticJsonSerde(AiAssessmentResult)
        ).value()
        ctx.set(
            "status",
            f"AI-based assessment completed: approved: {approved} reason: {approved.reason}",
        )
    else:
        # Loans over 1M require human assessment
        ctx.set("status", "Waiting for human assessment")
        await ctx.run("Request human assessment", request_human_assessment)
        approved = await ctx.promise("human_assessment").value()

    if not approved:
        ctx.set("status", "rejected")
        await invoke_agent(
            ctx,
            my_agents.notification_agent,
            "Send the customer a message that the loan got rejected",
        )
        return LoanDecision(approved=False)

    await invoke_agent(
        ctx,
        my_agents.notification_agent,
        "Send the customer a message that the loan got approved. Include an overview of the loan data.",
    )

    # 4. Deposit the loan amount to the customer account
    loan_transfer = account.Transaction(
        reason=f"Loan transfer {loan_request.customer_id}",
        amount=loan_request.loan_amount,
        timestamp=datetime.datetime.now().strftime("%Y-%m-%d")
    )
    await ctx.object_call(account.withdraw, key="TrustworthyBank", arg=loan_transfer)
    await ctx.object_call(
        account.deposit, key=loan_request.customer_id, arg=loan_transfer
    )

    # 5. Schedule recurring loan payments
    recurrent_payment = account.RecurringLoanPayment(
        monthly_amount=loan_request.loan_amount / loan_request.loan_duration_months,
        months_left=loan_request.loan_duration_months,
    )
    await ctx.object_call(
        account.on_recurring_loan_payment,
        key=loan_request.customer_id,
        arg=recurrent_payment,
    )

    return LoanDecision(approved=True)


@loan_approval_wf.handler()
async def on_human_assessment(ctx: restate.WorkflowSharedContext, approved: bool):
    await ctx.promise("human_assessment").resolve(approved)


class AiAssessmentResult(BaseModel):
    """
    The result of the AI assessment on whether the loan should be approved.

    Args:
        approved (bool): Whether the loan was approved or not.
        reason (str): The reason for the decision.
    """

    approved: bool
    reason: str


@loan_approval_wf.handler()
async def on_ai_assessment(
    ctx: restate.WorkflowSharedContext, assessment: AiAssessmentResult
):
    """
    This tool lets you approve or reject a loan based on the agent's review.

    Args:
        assessment (AiAssessmentResult): The result of the loan approval decision by the AI agent.
    """
    await ctx.promise(
        "agent_loan_review", serde=PydanticJsonSerde(AiAssessmentResult)
    ).resolve(assessment)


@loan_approval_wf.handler()
async def get_status(ctx: restate.WorkflowSharedContext) -> str:
    """
    Get the current status of the loan approval process.
    """
    return await ctx.get("status") or "unknown"


def request_human_assessment():
    pass


async def invoke_agent(ctx: restate.ObjectContext, starting_agent: Agent, msg: str):
    import my_agents
    ctx.object_send(
        agent_session_run,
        key=f"approval-workflow-{ctx.key()}",
        arg=AgentInput(
            starting_agent=starting_agent,
            agents=my_agents.agents,
            message=msg,
        ),
    )
