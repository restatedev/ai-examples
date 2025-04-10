import restate

from restate.exceptions import TerminalError

from loan_review_workflow import on_loan_decision
from utils.agent_session import restate_tool, RECOMMENDED_PROMPT_PREFIX, Agent, run as agent_session_run, AgentInput
from utils.pydantic_models import EnrichedTransactionHistory, CreditMetric, AdditionalInfoRequest

# TOOLS

"""
Tools to calculate credit worthiness metrics based on transaction history.
"""
credit_worthiness_svc = restate.Service("CreditWorthinessTools")


@credit_worthiness_svc.handler()
async def average_monthly_spending(
    ctx: restate.Context,
    transaction_history: EnrichedTransactionHistory,
) -> CreditMetric:
    """
    Calculate the average monthly spending over the last 12 months.

    Args:
        transaction_history (TransactionHistory): The user's transaction history.

    Returns:
        CreditMetric: The average monthly spending metric.
    """
    transactions = transaction_history.transactions
    expenses = [t.amount for t in transactions if t.amount < 0]
    return CreditMetric(label="average_monthly_spending", value=abs(sum(expenses) / 12))


@credit_worthiness_svc.handler()
async def debt_to_income_ratio(
    ctx: restate.Context,
    transaction_history: EnrichedTransactionHistory,
) -> CreditMetric:
    """
    Calculate the debt-to-income ratio.

    Args:
        transaction_history (TransactionHistory): The user's transaction history

    Returns:
        CreditMetric: The debt-to-income ratio metric.
    """
    transactions = transaction_history.transactions
    total_debt_payments = sum(
        t.amount for t in transactions if t.category == "loan_payment"
    )
    total_income = sum(
        t.amount for t in transactions if t.amount > 0 and t.category == "income"
    )
    return CreditMetric(
        label="debt_to_income_ratio",
        value=(
            (total_debt_payments / total_income) if total_income > 0 else float("inf")
        ),
    )


@credit_worthiness_svc.handler()
async def high_risk_transactions(
    ctx: restate.Context,
    transaction_history: EnrichedTransactionHistory,
) -> CreditMetric:
    """
    Calculate the number of high-risk transactions: gambling, payday loans, and cash withdrawals.

    Args:
        transaction_history (TransactionHistory): The user's transaction history

    Returns:
        CreditMetric: The number of high-risk transactions metric.
    """
    transactions = transaction_history.transactions
    risky_categories = {"gambling", "payday_loan", "cash_withdrawal"}
    return CreditMetric(
        label="high_risk_transactions",
        value=float(sum(1 for t in transactions if t.category in risky_categories)),
    )


@credit_worthiness_svc.handler()
async def large_purchases(
    ctx: restate.Context, transaction_history: EnrichedTransactionHistory
) -> CreditMetric:
    """
    Calculate the number of transactions that exceed 20% of the total income.

    Args:
        transaction_history (TransactionHistory): The user's transaction history

    Returns:
        CreditMetric: The number of large purchases metric.
    """
    transactions = transaction_history.transactions
    total_income = sum(
        t.amount for t in transactions if t.amount > 0 and t.category == "income"
    )
    threshold = total_income * 0.2
    return CreditMetric(
        label="large_purchases",
        value=float(sum(1 for t in transactions if abs(t.amount) > threshold)),
    )


"""
Tools to send information requests to the customer and route them back to the loan approval process.
"""
loan_review_agent_utils = restate.VirtualObject("LoanReviewAgentUtils")


@loan_review_agent_utils.handler()
async def request_additional_info(
    ctx: restate.ObjectContext,
    req: AdditionalInfoRequest,
) -> str:
    """
    This tool lets you send a message to the customer.
    The message will be sent to the customer with the given key.

    Args:
        key (str): The customer ID.
        message (str): The message to send.
    """
    from chat import add_async_response

    id, promise = ctx.awakeable()
    ctx.set("awakeable_id", id)

    # Send the message to the customer via the agent session which started the loan request.
    # Once the user will see the message and respond,
    # the agent which receives that message will route it back to us by resolving the promise.
    from chat import message_to_customer_agent, chat_agents
    print("Sending message to customer")
    ctx.object_send(agent_session_run, key=req.customer_id, arg=AgentInput(
        starting_agent=message_to_customer_agent,
        agents=chat_agents,
        message=f"""
        Use the add_async_response tool to send this CLARIFICATION REQUEST: {req.message}. 
        Once the customer answers to this use the Clarifications Answer Forwarder Agent - on_additional_info tool to route the answer back to the loan review agent.
        Don't respond to the customer directly. Just forward the answer.
        """,
        force_starting_agent=True))
    return await promise


@loan_review_agent_utils.handler(kind="shared")
async def on_additional_info(
    ctx: restate.ObjectSharedContext,
    msg: str,
) -> str:
    """
    This tool lets you route additional info supplied by the customer back to the loan approval process.
    Keyed by the loan ID.

    Args:
        msg (str): The message to route back.
    """
    awakeable_id = await ctx.get("awakeable_id")
    if awakeable_id is None:
        raise TerminalError("Response could not be routed back. There was no additional info request ongoing for this key. Did you use the correct key? ")

    ctx.resolve_awakeable(awakeable_id, msg)
    return "Response routed back successfully."



# ----- AGENTS ------

loan_review_agent = Agent(
    name="Loan Review Agent",
    handoff_description="A helpful agent that can helps you with reviewing loan requests based on the customer's creditworthiness.",
    instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
    You are an agent that helps with determining the creditworthiness of the customer.
    You decide on whether or not he should get a loan.  
    You were probably invoked by the loan approval workflow. 
    Use the following routine to support the customer, and never skip any of the steps.
    # Routine
    1. The input the loan approval workflow gave you contains the transaction history of the customer. 
    The first thing you should do is analyze the transaction history of the customer.
    You do this by categorizing each of the transactions into: income, loan_payment, gambling, payday_loan, cash_withdrawal, basic_expense, other.    
    2. Then you invoke each of the tools in parallel to calculate the important metrics to base your decision on: 
    - average_monthly_spending
    - debt_to_income_ratio
    - high_risk_transactions
    - large_purchases
    3. If any of these metrics are not good, then ask the customer for clarification by executing the request_additional_info tool with the loan ID as the key:
    - In the case of high_risk_transactions, ask for the reason of the high risk transactions.
    - In the case of large_purchases, ask for the reason of the large purchases.
    - In the case of debt_to_income_ratio, ask for the which other debts the customer has.
    Be very clear in the message about what you need to be clarified.
    4. Based on the metrics and clarifications,  make a decision to either approve or not. You can use your own judgement for this. 
    5. Let the loan approval workflow know the decision you made with the on_loan_decision tool with the loan ID as the key.
    Your decision contains a boolean on whether you approve on not, and your reasoning, together with the output of each of the tool call you did to calculate the metrics. 
    Make sure your reasoning is a kind, formal chat message, personalized for the customer. 
    Be very clear in the reason you give so the customer can understand the decision you made.
    Never skip this step.
    
    6. When you get a question or command that you don't understand, or you get asked to notify the customer, then transfer back to the Loan Request Processing Agent.
    """,
    tools=[
        restate_tool(on_loan_decision),
        restate_tool(average_monthly_spending),
        restate_tool(high_risk_transactions),
        restate_tool(debt_to_income_ratio),
        restate_tool(large_purchases),
        restate_tool(request_additional_info),
    ],
)