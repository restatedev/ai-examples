import restate

from utils.pydantic_models import EnrichedTransactionHistory, CreditMetric

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
