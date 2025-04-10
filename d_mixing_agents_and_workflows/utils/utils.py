import restate
import random

from datetime import datetime, timedelta

from utils.pydantic_models import TransactionHistory, Transaction

async def time_now(ctx: restate.WorkflowContext | restate.ObjectContext) -> int:
    return await ctx.run("time", lambda: round(datetime.now().timestamp() * 1000))


async def time_now_string(ctx: restate.WorkflowContext | restate.ObjectContext) -> str:
    return await ctx.run("time", lambda: datetime.now().strftime("%Y-%m-%d"))


regular_categories = {
    "income": ["Salary", "Bonus", "Freelance"],
    "loan_payment": ["Loan Repayment", "Mortgage Payment"],
    "cash_withdrawal": ["ATM Withdrawal"],
    "basic_expense": ["Groceries", "Rent", "Utilities"],
    "other": ["Gift", "Miscellaneous"],
}

high_risk_categories = {
    "gambling": ["Casino", "Lottery"],
    "payday_loan": ["Payday Loan Repayment"],
}


def generate_transactions() -> TransactionHistory:
    """
    Used to generate a random transaction history for the customer.
    To make the demo more interesting.
    """
    transactions = []
    start_date = datetime.now() - timedelta(days=365)
    for month in range(12):
        # Ensure one salary payment per month
        salary_date = start_date + timedelta(days=month * 30)
        transactions.append(
            Transaction(
                reason=f"Salary for month {month}",
                amount=4000.0,
                timestamp=salary_date.strftime("%Y-%m-%d"),
            )
        )

    for _ in range(10):
        category = random.choice(list(regular_categories.keys()))
        reason = random.choice(regular_categories[category])
        amount = round(random.uniform(-1000, 1000), 2)
        if category == "income":
            amount = abs(amount)
        else:
            amount = -abs(amount)
        date = start_date + timedelta(days=random.randint(0, 365))
        transactions.append(
            Transaction(
                reason=reason, amount=amount, timestamp=date.strftime("%Y-%m-%d")
            )
        )

    if random.random() > 0.5:
        # Add a few high-risk transaction
        for _ in range(6):
            category = random.choice(list(high_risk_categories.keys()))
            reason = random.choice(high_risk_categories[category])
            amount = round(random.uniform(-1000, 1000), 2)
            date = start_date + timedelta(days=random.randint(0, 365))
            transactions.append(
                Transaction(
                    reason=reason, amount=amount, timestamp=date.strftime("%Y-%m-%d")
                )
            )

    return TransactionHistory(transactions=transactions)
