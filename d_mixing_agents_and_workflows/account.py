import random
import restate

from datetime import timedelta

from utils.utils import time_now_string
from utils.pydantic_models import (
    Transaction,
    TransactionHistory,
    Loan,
    CustomerLoanOverview,
    RecurringLoanPayment,
    LoanRequest,
    LoanDecision,
    LoanReviewRequest,
)
from utils.utils import generate_transactions, time_now

# Keyed by customer ID
account = restate.VirtualObject("Account")


# Keys of the K/V state stored in Restate per account
BALANCE = "balance"
TRANSACTION_HISTORY = "transaction_history"
LOANS = "loans"


@account.handler()
async def deposit(ctx: restate.ObjectContext, transaction: Transaction):
    """
    Deposit money into the customer's account.

    Args:
        transaction (Transaction): The transaction object.
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

    Args:
        transaction (Transaction): The transaction object.
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
async def submit_loan_request(ctx: restate.ObjectContext, req: LoanRequest) -> str:
    """
    Submit a loan request.

    Args:
        req (LoanRequest): The loan request object.

    Returns:
        str: The loan ID
    """
    loan_id = await ctx.run("Generate Loan ID", lambda: str(random.randint(1000, 9999)))
    all_loans = await get_customer_loans(ctx)
    all_loans.loans[loan_id] = Loan(
        loan_id=loan_id,
        loan_request=req,
    )
    ctx.set(LOANS, all_loans)

    from loan_review_workflow import run

    loan_review_request = LoanReviewRequest(
        loan_request=req, transaction_history=await get_transaction_history(ctx)
    )
    ctx.workflow_send(run, key=loan_id, arg=loan_review_request)
    return loan_id


@account.handler()
async def process_loan_decision(ctx: restate.ObjectContext, decision: LoanDecision):
    """
    Update the loan status.

    Args:
        decision (LoanDecision): The loan decision object of whether the loan was approved or rejected.
    """
    all_loans = await get_customer_loans(ctx)
    loan = all_loans.loans.get(decision.loan_id)
    loan.loan_decision = decision
    loan.loan_payment = RecurringLoanPayment(
        monthly_amount=loan.loan_request.loan_amount
        / loan.loan_request.loan_duration_months,
        months_left=loan.loan_request.loan_duration_months,
    )
    ctx.set(LOANS, all_loans)

    await notify_customer(
        ctx,
        f"Loan {decision.loan_id} was {'approved' if decision.approved else 'rejected'} for the reason: {decision.reason}",
    )


@account.handler()
async def on_recurring_loan_payment(ctx: restate.ObjectContext, loan_id: str):
    """
    Handle a scheduled payment for a loan.

    Args:
        loan_id (str): The ID of the loan.
    """
    all_loans = await get_customer_loans(ctx)
    loan = all_loans.loans.get(loan_id)

    # Do the transfer back to the bank
    transaction = Transaction(
        reason=f"loan payment {loan_id}",
        amount=loan.monthly_amount,
        timestamp=await time_now_string(ctx),
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
    ctx.set(LOANS, all_loans)

    ctx.object_send(
        on_recurring_loan_payment,
        key=ctx.key(),
        arg=loan_id,
        send_delay=timedelta(days=30),
    )


@account.handler()
async def get_customer_loans(ctx: restate.ObjectContext) -> CustomerLoanOverview:
    """
    Get the ongoing loan requests and loan payments for the customer.

    Returns:
        CustomerLoanOverview: The overview of the customer's outstanding loans and loan requests.
    """
    return (
        await ctx.get(LOANS, type_hint=CustomerLoanOverview) or CustomerLoanOverview()
    )


@account.handler()
async def get_balance(ctx: restate.ObjectContext) -> float:
    """
    Get the balance of the customer.

    Returns:
        float: The balance of the customer.
    """
    return await ctx.get(BALANCE) or 100000.0


@account.handler()
async def get_transaction_history(ctx: restate.ObjectContext) -> TransactionHistory:
    """
    Get the transaction history of the customer.

    Returns:
        TransactionHistory: The transaction history of the customer.
    """
    # If there is no transaction history, return a default history of some salary payments
    history = await ctx.get(TRANSACTION_HISTORY, type_hint=TransactionHistory)
    if history is None:
        history = await ctx.run(
            "generate transactions",
            lambda: generate_transactions(),
            type_hint=TransactionHistory,
        )
        ctx.set(TRANSACTION_HISTORY, history)
    return history


async def notify_customer(ctx: restate.ObjectContext, message: str):
    """
    Notify the customer of a message.

    Args:
        message (str): The message to send to the customer.
    """
    # This could be any preferred contact method. Here we only have chat, so we send a chat message.
    from chat import ChatMessage, add_async_response

    chat_message = ChatMessage(
        role="system",
        content=message,
        timestamp_millis=await time_now(ctx),
    )
    ctx.object_send(add_async_response, key=ctx.key(), arg=chat_message)
