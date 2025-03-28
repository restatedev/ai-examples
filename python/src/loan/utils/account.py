import random
from datetime import timedelta, datetime

import restate
from pydantic import BaseModel
from restate.serde import PydanticJsonSerde

# Keyed by customer ID
account = restate.VirtualObject("Account")


class Transaction(BaseModel):
    reason: str
    amount: float
    timestamp: str


class TransactionHistory(BaseModel):
    transactions: list[Transaction]


class RecurringLoanPayment(BaseModel):
    monthly_amount: float
    months_left: int


@account.handler()
async def get_balance(ctx: restate.ObjectContext) -> float:
    """
    Get the balance of the customer.
    """
    return await ctx.get("balance") or 100000.0


@account.handler()
async def deposit(ctx: restate.ObjectContext, transaction: Transaction):
    """
    Deposit money into the customer's account.
    """
    balance = await get_balance(ctx)
    balance += transaction.amount
    ctx.set("balance", balance)

    history = await get_transaction_history(ctx)
    history.transactions.append(transaction)
    ctx.set("transaction_history", history, serde=PydanticJsonSerde(TransactionHistory))


@account.handler()
async def withdraw(ctx: restate.ObjectContext, transaction: Transaction):
    """
    Withdraw money from the customer's account.
    """
    balance = await get_balance(ctx)
    balance -= transaction.amount
    ctx.set("balance", balance)

    history = await get_transaction_history(ctx)
    history.transactions.append(transaction)
    ctx.set("transaction_history", history, serde=PydanticJsonSerde(TransactionHistory))


@account.handler()
async def calculate_credit_score(ctx: restate.ObjectContext) -> int:
    """
    Calculate the credit score of the customer.
    """
    return 80


@account.handler()
async def on_recurring_loan_payment(
    ctx: restate.ObjectContext, req: RecurringLoanPayment
):
    """
    Pay the loan amount.
    """
    # Do the transfer back to the bank
    transaction = Transaction(reason=f"loan payment {ctx.key()}", amount=req.monthly_amount, timestamp=datetime.now().strftime("%Y-%m-%d"))
    await withdraw(ctx, transaction)
    ctx.object_send(deposit, key="TrustworthyBank", arg=transaction)

    # If the loan is paid off, return
    if req.months_left == 0:
        return

    # Otherwise, schedule the next payment
    next_payment = RecurringLoanPayment(
        monthly_amount=req.monthly_amount, months_left=req.months_left - 1
    )
    ctx.object_send(
        on_recurring_loan_payment,
        key=ctx.key(),
        arg=next_payment,
        send_delay=timedelta(weeks=4),
    )


@account.handler()
async def get_transaction_history(ctx: restate.ObjectContext) -> TransactionHistory:
    """
    Get the transaction history of the customer.
    """
    # If there is no transaction history, return a default history of some salary payments
    history = await ctx.get("transaction_history", PydanticJsonSerde(TransactionHistory))
    if history is None:
        history = await ctx.run("generate transactions", lambda: generate_transactions(), serde=PydanticJsonSerde(TransactionHistory))
        ctx.set("transaction_history", history, serde=PydanticJsonSerde(TransactionHistory))
    return history


# --------------------Generate some transactions--------------------

categories = {
    "income": ["Salary", "Bonus", "Freelance"],
    "loan_payment": ["Loan Repayment", "Mortgage Payment"],
    "gambling": ["Casino", "Lottery"],
    "payday_loan": ["Payday Loan Repayment"],
    "cash_withdrawal": ["ATM Withdrawal"],
    "basic_expense": ["Groceries", "Rent", "Utilities"],
    "other": ["Gift", "Miscellaneous"],
}


def generate_transactions() -> TransactionHistory:
    transactions = []
    start_date = datetime.now() - timedelta(days=365)
    for month in range(12):
        # Ensure one salary payment per month
        salary_date = start_date + timedelta(days=month * 30)
        transactions.append(
            Transaction(
                reason=f"Salary for month {month}",
                amount=2000.0,
                timestamp=salary_date.strftime("%Y-%m-%d"),
            )
        )

    for _ in range(18):
        category = random.choice(list(categories.keys()))
        reason = random.choice(categories[category])
        amount = round(random.uniform(-1000, 1000), 2)
        date = start_date + timedelta(days=random.randint(0, 365))
        transactions.append(
            Transaction(
                reason=reason, amount=amount, timestamp=date.strftime("%Y-%m-%d")
            )
        )

    return TransactionHistory(transactions=transactions)
