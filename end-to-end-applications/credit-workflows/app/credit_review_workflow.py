import restate

from datetime import timedelta

from .utils.models import CreditReviewRequest, CreditDecision, CreditDecisionSerde
from .utils.utils import time_now_string
from .utils.agent_session import (
    AgentInput,
    run as agent_session_run,
)
from .account import (
    Transaction,
    process_credit_decision,
    withdraw as account_withdraw,
    deposit as account_deposit,
    on_recurring_credit_payment as account_credit_payment,
)

"""
The credit review workflow implements the process of reviewing a credit request.
The following steps are taken:

            +----------------------+
            | Receive Credit Request |
            +----------------------+
                      |
                      v
            +---------------------+
            | Credit Amount < 1M?   |
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
            | Wait for Credit Decision |  
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
| Return Decision     |   | Deposit Credit Amount |
+---------------------+   +---------------------+
                                  |
                                  v
                         +---------------------+
                         | Schedule Payments   |
                         +---------------------+
 """

credit_review_workflow = restate.Workflow("CreditApprovalWorkflow")


@credit_review_workflow.main()
async def run(
    ctx: restate.WorkflowContext, credit_review_request: CreditReviewRequest
) -> CreditDecision:
    """
    Run the credit approval workflow.

    Args:
        req (CreditRequest): The credit request object.
    """
    req = credit_review_request.credit_request
    # 1. Assess the credit request
    if req.credit_amount < 1000000:
        # Credits under 1M can be approved by the AI agent
        history = credit_review_request.transaction_history.model_dump_json()
        credit_intake_data = (
            f"Credit approval workflow ID: {ctx.key()} --> Use this key to communicate back to the workflow."
            f"Review the credit request: {req.model_dump_json()};"
            f"transaction history: {history};"
        )
        from .credit_review_agent import credit_review_agent

        ctx.object_send(
            agent_session_run,
            key=ctx.key(),
            arg=AgentInput(
                starting_agent=credit_review_agent,
                agents=[credit_review_agent],
                message=credit_intake_data,
            ),
        )
    else:
        # Credits over 1M require human assessment
        await ctx.run("Request human assessment", request_human_assessment)

    # 2. Wait for the credit decision and add the info to the customer account
    decision = await ctx.promise("credit_decision", serde=CreditDecisionSerde).value()
    ctx.object_send(process_credit_decision, key=req.customer_id, arg=decision)

    if not decision.approved:
        return decision

    # 3. Deposit the credit amount to the customer account
    credit_transfer = Transaction(
        reason=f"Credit transfer {req.customer_id}",
        amount=req.credit_amount,
        timestamp=await time_now_string(ctx),
    )
    await ctx.object_call(account_withdraw, key="TrustworthyBank", arg=credit_transfer)
    await ctx.object_call(account_deposit, key=req.customer_id, arg=credit_transfer)

    # 4. Schedule recurring credit payments to start in one month
    ctx.object_send(
        account_credit_payment,
        key=req.customer_id,
        arg=ctx.key(),
        send_delay=timedelta(days=30),
    )
    return decision


@credit_review_workflow.handler()
async def on_credit_decision(ctx: restate.WorkflowSharedContext, decision: CreditDecision):
    """
    This tool lets you approve or reject a credit.

    Args:
        decision (CreditDecision): The result of the credit approval decision.
    """
    await ctx.promise("credit_decision", serde=CreditDecisionSerde).resolve(decision)


# ----- UTILS ------


def request_human_assessment():
    # request a credit assessor to have a look
    # ... to be implemented ...
    pass
