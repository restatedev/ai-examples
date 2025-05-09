import restate

from datetime import timedelta

from .utils.pydantic_models import LoanReviewRequest, LoanDecision, LoanDecisionSerde
from .utils.utils import time_now_string
from .utils.agent_session import (
    AgentInput,
    run as agent_session_run,
)
from .account import (
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
        from .loan_review_agent import loan_review_agent

        ctx.object_send(
            agent_session_run,
            key=ctx.key(),
            arg=AgentInput(
                starting_agent=loan_review_agent,
                agents=[loan_review_agent],
                message=loan_intake_data,
            ),
        )
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


# ----- UTILS ------


def request_human_assessment():
    # request a loan assessor to have a look
    # ... to be implemented ...
    pass
