import restate

from datetime import timedelta

from utils.pydantic_models import LoanReviewRequest, LoanDecision, LoanDecisionSerde
from utils.utils import time_now_string
from utils.agent_session import (
    AgentInput,
    RECOMMENDED_PROMPT_PREFIX,
    Agent,
    restate_tool,
    run as agent_session_run,
)
from utils.credit_worthiness_tools import (
    average_monthly_spending,
    debt_to_income_ratio,
    high_risk_transactions,
    large_purchases,
)
from account import (
    Transaction,
    process_loan_decision,
    withdraw as account_withdraw,
    deposit as account_deposit,
    on_recurring_loan_payment as account_loan_payment,
)

"""
The loan review workflow implements the process of reviewing a loan request.
The following steps are taken:

            +----------------------+
            | Receive Loan Request |
            +----------------------+
                      |
                      v
            +---------------------+
            | Loan Amount < 1M?   |
            +---------------------+
              /                    \
            Yes                     No
            /                        \
           v                          v
+---------------------+   +----------------------+
|  Invoke AI Agent    |   | Request Human Review |
+---------------------+   +----------------------+
             \                  /
              v                v  
            +------------------------+  
            | Wait for Loan Decision |  
            +------------------------+  
                      |                     
                      v                     
            +---------------------+   
            | Decision Approved?  |   
            +---------------------+   
                /         \        
               No         Yes      
              /             \      
             v               v     
+---------------------+   +---------------------+
| Return Decision     |   | Deposit Loan Amount |
+---------------------+   +---------------------+
                                  |
                                  v
                         +---------------------+
                         | Schedule Payments   |
                         +---------------------+
 """

loan_review_workflow = restate.Workflow("LoanApprovalWorkflow")


@loan_review_workflow.main()
async def run(
    ctx: restate.WorkflowContext, loan_review_request: LoanReviewRequest
) -> LoanDecision:
    """
    Run the loan approval workflow.

    Args:
        req (LoanRequest): The loan request object.
    """
    req = loan_review_request.loan_request
    # 1. Assess the loan request
    if req.loan_amount < 1000000:
        # Loans under 1M can be approved by the AI agent
        history = loan_review_request.transaction_history.model_dump_json()
        loan_intake_data = (
            f"Loan approval workflow ID: {ctx.key()} --> Use this key to communicate back to the workflow."
            f"Review the loan request: {req.model_dump_json()};"
            f"transaction history: {history};"
        )
        await invoke_agent(ctx, loan_intake_data)
    else:
        # Loans over 1M require human assessment
        await ctx.run("Request human assessment", request_human_assessment)

    # 2. Wait for the loan decision and add the info to the customer account
    decision = await ctx.promise("loan_decision", serde=LoanDecisionSerde).value()
    ctx.object_send(process_loan_decision, key=req.customer_id, arg=decision)

    if not decision.approved:
        return decision

    # 3. Deposit the loan amount to the customer account
    loan_transfer = Transaction(
        reason=f"Loan transfer {req.customer_id}",
        amount=req.loan_amount,
        timestamp=await time_now_string(ctx),
    )
    await ctx.object_call(account_withdraw, key="TrustworthyBank", arg=loan_transfer)
    await ctx.object_call(account_deposit, key=req.customer_id, arg=loan_transfer)

    # 4. Schedule recurring loan payments to start in one month
    ctx.object_send(
        account_loan_payment,
        key=req.customer_id,
        arg=ctx.key(),
        send_delay=timedelta(days=30),
    )
    return decision


@loan_review_workflow.handler()
async def on_loan_decision(ctx: restate.WorkflowSharedContext, decision: LoanDecision):
    """
    This tool lets you approve or reject a loan.

    Args:
        decision (LoanDecision): The result of the loan approval decision.
    """
    await ctx.promise("loan_decision", serde=LoanDecisionSerde).resolve(decision)


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
        restate_tool(on_loan_decision),
        restate_tool(average_monthly_spending),
        restate_tool(high_risk_transactions),
        restate_tool(debt_to_income_ratio),
        restate_tool(large_purchases),
    ],
)

# ----- UTILS ------


def request_human_assessment():
    # request a loan assessor to have a look
    # ... to be implemented ...
    pass


async def invoke_agent(ctx: restate.ObjectContext, msg: str):
    ctx.object_send(
        agent_session_run,
        key=ctx.key(),  # Same key as workflow
        arg=AgentInput(
            starting_agent=loan_review_agent,
            agents=[loan_review_agent],
            message=msg,
        ),
    )
