from email.policy import default

import restate
from pydantic import BaseModel
from typing import List, Literal

TransactionCategory = Literal[
    "income",
    "loan_payment",
    "gambling",
    "payday_loan",
    "cash_withdrawal",
    "basic_expense",
    "other",
]


class EnrichedTransaction(BaseModel):
    """
    A single transaction in a customer account.

    Args:
        amount (float): The amount of the transaction. Negative for expenses, positive for income
        category (TransactionCategory): The category of the transaction.  # e.g., "income", "loan_payment", "gambling", etc.
        timestamp (str): The timestamp of the transaction in YYYY-MM-DD format
        balance_after (float): The balance after the transaction.
    """

    amount: float
    category: TransactionCategory
    timestamp: str
    reason: str


class EnrichedTransactionHistory(BaseModel):
    """
    A customer account's transaction history enriched with categories.

    Args:
        transactions (List[Transaction]): A list of transactions
    """

    transactions: List[EnrichedTransaction]


class CreditMetric(BaseModel):
    """
    A credit worthiness outcome.

    Args:
        value (float): The value of the outcome
        label (str): The name of the metric
    """

    label: str
    value: float


class CreditMetricList(BaseModel):
    """
    A list of credit worthiness outcomes.

    Args:
        metrics (List[CreditMetric]): A list of credit worthiness outcomes
    """

    metrics: List[CreditMetric]


credit_worthiness_svc = restate.Service("CreditWorthinessTools")


@credit_worthiness_svc.handler()
async def average_monthly_spending(
    ctx: restate.Context, transaction_history: EnrichedTransactionHistory,
) -> CreditMetric:
    """
    Calculate the average monthly spending over the last 12 months.

    Args:
        transaction_history (TransactionHistory): The user's transaction history.
    """
    transactions = transaction_history.transactions
    expenses = [t.amount for t in transactions if t.amount < 0]
    return CreditMetric(label="average_monthly_spending", value=abs(sum(expenses) / 12))


@credit_worthiness_svc.handler()
async def debt_to_income_ratio(
    ctx: restate.Context, transaction_history: EnrichedTransactionHistory,
) -> CreditMetric:
    """
    Calculate the debt-to-income ratio.

    Args:
        transaction_history (TransactionHistory): The user's transaction history
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
    ctx: restate.Context, transaction_history: EnrichedTransactionHistory,
) -> CreditMetric:
    """
    Calculate the number of high-risk transactions: gambling, payday loans, and cash withdrawals.

    Args:
        transaction_history (TransactionHistory): The user's transaction history
    """
    transactions = transaction_history.transactions
    risky_categories = {"gambling", "payday_loan", "cash_withdrawal"}
    return CreditMetric(
        label="high_risk_transactions",
        value=float(sum(1 for t in transactions if t.category in risky_categories)),
    )


@credit_worthiness_svc.handler()
async def large_purchases(ctx: restate.Context, transaction_history: EnrichedTransactionHistory) -> CreditMetric:
    """
    Calculate the number of transactions that exceed 20% of the total income.

    Args:
        transaction_history (TransactionHistory): The user's transaction history
        threshold (float): The threshold for large purchases
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
