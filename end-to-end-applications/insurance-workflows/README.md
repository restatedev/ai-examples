
## Mixing static, code-defined workflows with agentic workflows

**Note:** We didn't need to change anything in the agent loop to make this work.

The agent session we implemented in the previous section is just a Restate Virtual Object. 
It can be called from anywhere, also from a more traditional code-defined workflow. 
For example, imagine a [loan approval workflow](insurance_workflows/loan_review_workflow.py) where a step in the workflow is to wait on an [agent to analyze the loan application](insurance_workflows/loan_review_agent.py) and interact with the customer to request additional information if necessary.

Benefits of Restate here:
- Benefits of previous section.
- **A single workflow orchestrator that handles both agentic and traditional workflows and gives the same resiliency guarantees and observability across both.**


<img src="img/mixing_agentic_and_traditional.png" alt="Loan workflow with agentic step" width="650px"/>

An example workflow in detail ([code](insurance_workflows/loan_review_workflow.py)):

<img src="img/mixing_agents_and_workflow.png" alt="Loan workflow" width="650px"/>

Or in code:
```python
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
        from loan_review_agent import loan_review_agent
        ctx.object_send(
            agent_session_run,
            key=ctx.key(),
            arg=AgentInput(
                starting_agent=loan_review_agent,
                agents=[loan_review_agent],
                message=loan_intake_data,
            )
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
```

[<img src="https://raw.githubusercontent.com/restatedev/img/refs/heads/main/play-button.svg" width="16" height="16"> Run the example](#mixing-static-code-defined-workflows-with-agentic-workflows-1)


### Mixing static, code-defined workflows with agentic workflows

In this [full example](#running-the-loan-approval-app-mixing-agents-and-workflows), the loan workflow is kicked off by an agentic chat session. 
It lets you interact with a [loan workflow agent](insurance_workflows) that can apply for loans, check the status of loans, and provide information about bank accounts.

The loan workflow then again starts an agent session to review the loan application and interact with the customer to request additional information if necessary.

The application looks as follows:

<img src="img/loan_approval_agents.png" alt="Loan workflow app overview" width="650px"/>

You need to export your OPENAI API key as an environment variable:

```shell
export OPENAI_API_KEY=your_openai_api_key
```

To run the loan approval app::

```shell
python3 d_mixing_agents_and_workflows/main.py
```

To run Restate:
```shell
restate-server
```
Register your deployment in the UI: `http://localhost:9080`

Start the chat UI:
```shell
cd ui
npm i 
npm run dev
```

Open a new chat session on http://localhost:3000 and request a loan, the status of an ongoing loans or information about your bank account from the UI. 

For example:
```
Hi, I would like to apply for a loan of 1000 euros. 
```

Or:
```
Hi, what is the status of my loan?
```

When you apply for a loan the agent will kick off the loan workflow.
And you will get async updates about whether your loan has been approved or not.

<img src="img/chat_example.png" alt="Chat example"/>

Here is an example of a journal of a loan application which required extra info:

<img src="img/mixing_agents_and_workflows_journal.png" alt="Loan journal"/>

