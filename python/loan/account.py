import random
from datetime import timedelta, datetime
from typing import Dict

import restate
from pydantic import BaseModel, Field

from loan_review_workflow import LoanRequest, LoanDecision
from loan_review_workflow import run as run_loan_review_workflow, get_status as get_status_loan_review_workflow

# Keyed by customer ID
account = restate.VirtualObject("Account")


# --------------------Models--------------------

class Transaction(BaseModel):
    reason: str
    amount: float
    timestamp: str


class TransactionHistory(BaseModel):
    transactions: list[Transaction]


class RecurringLoanPayment(BaseModel):
    monthly_amount: float
    months_left: int


class Loan(BaseModel):
    """
    A loan object.

    Args:
        loan_id (str): The ID of the loan.
        loan_amount (int): The amount of the loan.
        loan_duration_months (int): The duration of the loan in months.
    """

    loan_id: str
    loan_request: LoanRequest
    loan_decision: LoanDecision | None = Field(default=None)
    loan_payment: RecurringLoanPayment | None = Field(default=None)


class CustomerLoanOverview(BaseModel):
    """
    The ongoing loan requests and loan payments for the customer.

    Args:
        loans (Dict[str, Loan]): The list of loans.
    """
    loans: Dict[str, Loan] = Field(default={})


# --------------------Account Service--------------------

# K/V state per account
BALANCE = "balance"
TRANSACTION_HISTORY = "transaction_history"
LOANS = "loans"


@account.handler()
async def deposit(ctx: restate.ObjectContext, transaction: Transaction):
    """
    Deposit money into the customer's account.
    """
    balance = await get_balance(ctx)
    balance += abs(transaction.amount)
    ctx.set(BALANCE, balance)

    history = await get_transaction_history(ctx)
    history.transactions.append(transaction)
    ctx.set(TRANSACTION_HISTORY, history)


@account.handler()
async def withdraw(ctx: restate.ObjectContext, transaction: Transaction):
    """
    Withdraw money from the customer's account.
    """
    balance = await get_balance(ctx)
    balance -= abs(transaction.amount)
    ctx.set(BALANCE, balance)

    # Make sure this is a negative transaction
    transaction.amount = -abs(transaction.amount)
    history = await get_transaction_history(ctx)
    history.transactions.append(transaction)
    ctx.set(TRANSACTION_HISTORY, history)


@account.handler()
async def get_balance(ctx: restate.ObjectContext) -> float:
    """
    Get the balance of the customer.
    """
    return await ctx.get(BALANCE) or 100000.0


@account.handler()
async def get_transaction_history(ctx: restate.ObjectContext) -> TransactionHistory:
    """
    Get the transaction history of the customer.
    """
    # If there is no transaction history, return a default history of some salary payments
    history = await ctx.get(
        TRANSACTION_HISTORY, type_hint=TransactionHistory
    )
    if history is None:
        history = await ctx.run(
            "generate transactions",
            lambda: generate_transactions(),
            type_hint=TransactionHistory,
        )
        ctx.set(TRANSACTION_HISTORY, history)
    return history


@account.handler()
async def submit_loan_request(ctx: restate.ObjectContext, loan_request: LoanRequest) -> str:
    """
    Submit a loan request.

    Args:
        loan_request (LoanRequest): The loan request object.
    """
    all_customer_loans = await ctx.get(LOANS, type_hint=CustomerLoanOverview) or CustomerLoanOverview()

    loan_id = await ctx.run("Generate Loan ID", lambda: str(random.randint(1000, 9999)))
    all_customer_loans.loans[loan_id] = Loan(
        loan_id=loan_id,
        loan_request=loan_request,
    )
    ctx.set(LOANS, all_customer_loans)

    ctx.workflow_send(run_loan_review_workflow, key=loan_id, arg=loan_request)
    return f"Loan request submitted successfully with ID {loan_id}."


@account.handler()
async def get_customer_loans(ctx: restate.ObjectContext) -> CustomerLoanOverview:
    """
    Get the ongoing loan requests and loan payments for the customer.
    """
    all_customer_loans = await ctx.get(LOANS, type_hint=CustomerLoanOverview) or CustomerLoanOverview()
    return all_customer_loans


@account.handler()
async def process_loan_decision(ctx: restate.ObjectContext, decision: LoanDecision):
    """
    Update the loan status.
    """
    all_customer_loans = await ctx.get(LOANS, type_hint=CustomerLoanOverview) or CustomerLoanOverview()
    loan = all_customer_loans.loans.get(decision.loan_id)
    loan.loan_decision = decision
    this_loan_request = loan.loan_request
    loan.loan_payment = RecurringLoanPayment(
        monthly_amount=this_loan_request.loan_amount / this_loan_request.loan_duration_months,
        months_left=this_loan_request.loan_duration_months,
    )
    ctx.set(LOANS, all_customer_loans)

    await notify_customer(ctx, f"Loan {decision.loan_id} was {'approved' if decision.approved else 'rejected'} for the reason: {decision.reason}")


@account.handler()
async def calculate_credit_score(ctx: restate.ObjectContext) -> int:
    """
    Calculate the credit score of the customer.
    """
    return 300


@account.handler()
async def on_recurring_loan_payment(
    ctx: restate.ObjectContext, loan_id: str
):
    """
    Pay the loan amount.
    """
    all_customer_loans = await ctx.get(LOANS, type_hint=CustomerLoanOverview) or CustomerLoanOverview()
    loan = all_customer_loans.loans.get(loan_id)

    # Do the transfer back to the bank
    time_now = await ctx.run("tx time", lambda: datetime.now().strftime("%Y-%m-%d"))
    transaction = Transaction(
        reason=f"loan payment {loan_id}",
        amount=loan.monthly_amount,
        timestamp=time_now,
    )
    await withdraw(ctx, transaction)
    ctx.object_send(deposit, key="TrustworthyBank", arg=transaction)

    # If the loan is paid off, return
    if loan.months_left == 1:
        return

    # Otherwise, schedule the next payment
    loan.loan_payment = RecurringLoanPayment(
        monthly_amount=loan.monthly_amount, months_left=loan.months_left - 1
    )
    ctx.set(LOANS, all_customer_loans)

    ctx.object_send(
        on_recurring_loan_payment,
        key=ctx.key(),
        arg=loan_id,
        send_delay=timedelta(days=30),
    )


# --------------------UTILS--------------------

async def notify_customer(ctx: restate.ObjectContext, message: str):
    """
    Notify the customer about the loan decision.
    """
    # This could be any preferred contact method. Here we only have chat, so we send a chat message.
    from chat import ChatMessage, receive_message
    time_now = await ctx.run("time", lambda: round(datetime.now().timestamp() * 1000))
    chat_message = ChatMessage(
        role="system",
        content=message,
        timestamp= time_now,
    )
    ctx.object_send(receive_message, key=ctx.key(), arg=chat_message)


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
                amount=2000.0,
                timestamp=salary_date.strftime("%Y-%m-%d"),
            )
        )

    for _ in range(18):
        category = random.choice(list(categories.keys()))
        reason = random.choice(categories[category])
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

    return TransactionHistory(transactions=transactions)
