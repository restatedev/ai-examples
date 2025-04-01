import datetime

import restate
from pydantic import BaseModel, Field
from restate.serde import PydanticJsonSerde

from utils.agent_session import AgentInput, RECOMMENDED_PROMPT_PREFIX, Agent, restate_tool
from utils.agent_session import run as agent_session_run
from utils.credit_worthiness_tools import average_monthly_spending, debt_to_income_ratio, high_risk_transactions, large_purchases
import chat

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

    events: list[str] = Field(default=[])



class LoanDecision(BaseModel):
    """
    A loan decision object.

    Args:
        loan_id (str): The ID of the loan.
        approved (bool): Whether the loan was approved or not.
        reason (str): The reason for the decision.
    """
    loan_id: str
    approved: bool
    reason: str


DecisionSerde = PydanticJsonSerde(LoanDecision)

# ----- LOAN APPROVAL WORKFLOW ------

loan_review_workflow = restate.Workflow("LoanApprovalWorkflow")


@loan_review_workflow.main()
async def run(ctx: restate.WorkflowContext, loan_request: LoanRequest) -> LoanDecision:
    """
    Run the loan approval workflow.

    Args:
        loan_request (LoanRequest): The loan request object.
    """
    from account import Transaction, process_loan_decision, withdraw as account_withdraw, deposit as account_deposit, on_recurring_loan_payment as account_loan_payment, get_transaction_history as account_get_transaction_history

    customer_id = loan_request.customer_id
    await update_status(ctx, "Submitted")

    # 1. Gather extra info on the customer
    # TODO this can move to the account service
    transaction_history = await ctx.object_call(
        account_get_transaction_history, key=customer_id, arg=None
    )

    # 2. Run the loan approval process
    if loan_request.loan_amount < 1000000:
        # Loans under 1M can be approved by the AI agent
        await update_status(ctx, "Running AI-based assessment")
        loan_intake_data = (
            f"Loan approval workflow ID: {ctx.key()} --> Use this key to communicate back to the workflow."
            f"Review the loan request: {loan_request.model_dump_json()};"
            f"transaction history: {transaction_history.model_dump_json()};"
        )
        await invoke_agent(ctx, loan_intake_data)
    else:
        # Loans over 1M require human assessment
        await update_status(ctx, "Waiting for human assessment")
        await ctx.run("Request human assessment", request_human_assessment)

    # 3. Wait for the loan decision and notify the customer
    decision = await ctx.promise("loan_decision", serde=DecisionSerde).value()
    ctx.object_send(process_loan_decision, key=customer_id, arg=decision)
    await update_status(ctx, f"Loan decision: {decision.model_dump_json()}")

    if not decision.approved:
        return decision

    # 4. Deposit the loan amount to the customer account
    tx_time = await ctx.run(
        "tx time", lambda: datetime.datetime.now().strftime("%Y-%m-%d")
    )
    loan_transfer = Transaction(
        reason=f"Loan transfer {customer_id}",
        amount=loan_request.loan_amount,
        timestamp=tx_time,
    )
    await ctx.object_call(account_withdraw, key="TrustworthyBank", arg=loan_transfer)
    await ctx.object_call(account_deposit, key=customer_id, arg=loan_transfer)
    await update_status(ctx, f"Money transferred to customer account {customer_id}")

    # 5. Schedule recurring loan payments to start in one month
    ctx.object_send(account_loan_payment, key=customer_id, arg=ctx.key(), send_delay=datetime.timedelta(days=30))
    await update_status(ctx, f"Recurring loan payment scheduled for {customer_id}")
    return decision


@loan_review_workflow.handler()
async def on_loan_decision(ctx: restate.WorkflowSharedContext, decision: LoanDecision):
    """
    This tool lets you approve or reject a loan.

    Args:
        decision (LoanDecision): The result of the loan approval decision.
    """
    print(f"Approving loan {ctx.key()} with decision {decision.model_dump_json()}")
    await ctx.promise("loan_decision", serde=DecisionSerde).resolve(decision)

@loan_review_workflow.handler()
async def get_status(ctx: restate.WorkflowSharedContext) -> LoanStatus:
    """
    Get the current status of the loan approval process.
    """
    return await ctx.get("status", type_hint=LoanStatus) or LoanStatus()



# ----- AGENTS ------

loan_review_agent = Agent(
    name="Loan Review Agent",
    handoff_description="A helpful agent that can helps you with reviewing loan requests based on the customer's creditworthiness.",
    instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
    You are an agent that helps with determining the creditworthiness of the customer.
    You decide on whether or not he should get a loan.  
    You were probably invoked by the loan approval workflow. 
    Use the following routine to support the customer.
    # Routine
    1. The input the loan approval workflow gave you contains the credit score, and transaction history of the customer. 
    The first thing you should do is analyze the transaction history of the customer.
    You do this by categorizing each of the transactions into: income, loan_payment, gambling, payday_loan, cash_withdrawal, basic_expense, other.    
    2. Then you invoke each of the tools in parallel to calculate the important metrics to base your decision on: 
    - average_monthly_spending
    - debt_to_income_ratio
    - high_risk_transactions
    - large_purchases
    3. Based on the values you get back you then make a decision to either approve or not. You can use your own judgement for this. 
    4. Invoke the on_loan_decision tool to then let the workflow know of your decision. This lets the workflow know the decision, not the customer!
    Use the loan approval workflow ID as the key when you invoke the on_loan_decision handler. 
    Your decision contains a boolean on whether you approve on not, and your reasoning, together with the output of each of the tool call you did to calculate the metrics. 
    Make sure your reasoning is a kind, formal chat message, personalized for the customer. 
    Be very clear in the reason you give so the customer can understand the decision you made.
    In case of any doubt, reject the loan application, and give as reason "NOT ENOUGH INFORMATION" together with the output of each of the tools.
    5. When you get a question or command that you don't understand, or you get asked to notify the customer, then transfer back to the Loan Request Processing Agent.
    """,
    tools=[
        restate_tool(tool_call=on_loan_decision),
        restate_tool(tool_call=average_monthly_spending),
        restate_tool(tool_call=high_risk_transactions),
        restate_tool(tool_call=debt_to_income_ratio),
        restate_tool(tool_call=large_purchases)
    ],
)

# ----- UTILS ------

def request_human_assessment():
    # request a loan assessor to have a look
    # ... to be implemented ...
    pass


async def update_status(ctx: restate.WorkflowContext, msg):
    """
    Update the status of the loan approval process.
    """
    status = await ctx.get("status", type_hint=LoanStatus) or LoanStatus(events=[])
    status.events.append(msg)
    ctx.set("status", status)


async def invoke_agent(ctx: restate.ObjectContext, msg: str):
    ctx.object_send(
        agent_session_run,
        key=ctx.key(), # Same key as workflow
        arg=AgentInput(
            starting_agent=loan_review_agent,
            agents=[loan_review_agent],
            message=msg,
        ),
    )
