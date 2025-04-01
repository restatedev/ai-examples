import datetime

import restate
from pydantic import BaseModel
from restate.serde import PydanticJsonSerde

import utils.account as account
from utils.account import Transaction
from utils.account import RecurringLoanPayment
from utils.agent_session import AgentInput
from utils.agent_session import run as agent_session_run

# ----- MODELS ------

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


class LoanStatus(BaseModel):
    """
    A loan status object.

    Args:
        status (str): The current status of the loan approval process.
    """

    events: list[str]



class LoanDecision(BaseModel):
    """
    A loan decision object.

    Args:
        approved (bool): Whether the loan was approved or not.
        reason (str): The reason for the decision.
    """

    approved: bool
    reason: str


DecisionSerde = PydanticJsonSerde(LoanDecision)

# ----- LOAN APPROVAL WORKFLOW ------

loan_approval_wf = restate.Workflow("LoanApprovalWorkflow")


@loan_approval_wf.main()
async def run(ctx: restate.WorkflowContext, loan_request: LoanRequest) -> LoanDecision:
    """
    Run the loan approval workflow.

    Args:
        loan_request (LoanRequest): The loan request object.
    """
    customer_id = loan_request.customer_id
    await update_status(ctx, "Submitted")

    # 1. Gather extra info on the customer
    credit_score = await ctx.object_call(
        account.calculate_credit_score, key=customer_id, arg=None
    )
    transaction_history = await ctx.object_call(
        account.get_transaction_history, key=customer_id, arg=None
    )

    # 2. Run the loan approval process
    if loan_request.loan_amount < 1000000:
        # Loans under 1M can be approved by the AI agent
        await update_status(ctx, "Running AI-based assessment")
        loan_intake_data = (
            f"Loan approval workflow ID: {ctx.key()} --> Use this key to communicate back to the workflow."
            f"Review the loan request: {loan_request.model_dump_json()};"
            f"credit score:{credit_score};"
            f"transaction history: {transaction_history.model_dump_json()};"
        )
        await invoke_agent(ctx, loan_intake_data)
    else:
        # Loans over 1M require human assessment
        await update_status(ctx, "Waiting for human assessment")
        await ctx.run("Request human assessment", request_human_assessment)

    # 3. Wait for the loan decision and notify the customer
    decision = await ctx.promise("loan_decision", serde=DecisionSerde).value()
    await update_status(ctx, f"Loan decision: {decision.model_dump_json()}")

    if not decision.approved:
        rejection_msg = f"Notify customer with ID {loan_request.customer_id} that the loan got rejected"
        await invoke_agent(ctx, rejection_msg)
        return decision

    approval_msg = (
        f"Notify customer with ID {loan_request.customer_id} that the loan got approved and a loan overview."
    )
    await invoke_agent(ctx, approval_msg)

    # 4. Deposit the loan amount to the customer account
    loan_transfer = await as_transaction(ctx, customer_id, loan_request.loan_amount)
    await ctx.object_call(account.withdraw, key="TrustworthyBank", arg=loan_transfer)
    await ctx.object_call(account.deposit, key=customer_id, arg=loan_transfer)
    await update_status(ctx, f"Money transferred to customer account {customer_id}")

    # 5. Schedule recurring loan payments
    recurrent_payment = RecurringLoanPayment(
        monthly_amount=loan_request.loan_amount / loan_request.loan_duration_months,
        months_left=loan_request.loan_duration_months,
    )
    await ctx.object_call(
        account.on_recurring_loan_payment, key=customer_id, arg=recurrent_payment
    )
    await update_status(ctx, f"Recurring loan payment scheduled for {customer_id}")
    return decision


@loan_approval_wf.handler()
async def on_loan_decision(ctx: restate.WorkflowSharedContext, decision: LoanDecision):
    """
    This tool lets you approve or reject a loan.

    Args:
        decision (LoanDecision): The result of the loan approval decision.
    """
    print(f"Approving loan {ctx.key()} with decision {decision.model_dump_json()}")
    await ctx.promise("loan_decision", serde=DecisionSerde).resolve(decision)

@loan_approval_wf.handler()
async def get_status(ctx: restate.WorkflowSharedContext) -> LoanStatus:
    """
    Get the current status of the loan approval process.
    """
    return await ctx.get("status", type_hint=LoanStatus) or LoanStatus(events=["No events registered for this loan approval workflow."])


# ----- UTILS ------


def request_human_assessment():
    pass


async def update_status(ctx: restate.WorkflowContext, msg):
    """
    Update the status of the loan approval process.
    """
    status = await ctx.get("status", type_hint=LoanStatus) or LoanStatus(events=[])
    status.events.append(msg)
    ctx.set("status", status)


async def as_transaction(
    ctx: restate.WorkflowContext, customer_id: str, loan_amount: int
) -> Transaction:
    tx_time = await ctx.run(
        "tx time", lambda: datetime.datetime.now().strftime("%Y-%m-%d")
    )
    return Transaction(
        reason=f"Loan transfer {customer_id}",
        amount=loan_amount,
        timestamp=tx_time,
    )


async def invoke_agent(ctx: restate.ObjectContext, msg: str):
    import my_agents

    ctx.object_send(
        agent_session_run,
        key=ctx.key(),
        arg=AgentInput(
            starting_agent=my_agents.loan_processing_agent,
            agents=my_agents.agents,
            message=msg,
        ),
    )
