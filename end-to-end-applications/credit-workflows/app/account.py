import random
import restate

from datetime import timedelta

from .utils.utils import time_now_string
from .utils.models import (
    Transaction,
    TransactionHistory,
    Credit, CreditRequest, CreditReviewRequest, CreditDecision, RecurringCreditPayment, CustomerCreditOverview,
)
from .utils.utils import generate_transactions, time_now

# Keyed by customer ID
account = restate.VirtualObject("Account")


# Keys of the K/V state stored in Restate per account
BALANCE = "balance"
TRANSACTION_HISTORY = "transaction_history"
CREDITS = "credits"


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
async def submit_credit_request(ctx: restate.ObjectContext, req: CreditRequest) -> str:
    """
    Let the customer submit a credit request for a specified duration and amount.

    Args:
        req (CreditRequest): The credit request object.

    Returns:
        str: The credit ID
    """
    credit_id = await ctx.run(
        "Generate Credit ID", lambda: "credit-" + str(random.randint(1000, 9999))
    )
    all_credits = await get_customer_credits(ctx)
    all_credits.credits[credit_id] = Credit(
        credit_id=credit_id,
        credit_request=req,
    )
    ctx.set(CREDITS, all_credits)

    from .credit_review_workflow import run

    credit_review_request = CreditReviewRequest(
        credit_request=req, transaction_history=await get_transaction_history(ctx)
    )
    ctx.workflow_send(run, key=credit_id, arg=credit_review_request)
    return f"The credit request with {credit_id} was scheduled for review."


@account.handler()
async def process_credit_decision(ctx: restate.ObjectContext, decision: CreditDecision):
    """
    Update the credit status.

    Args:
        decision (CreditDecision): The credit decision object of whether the credit was approved or rejected.
    """
    all_credits = await get_customer_credits(ctx)
    credit = all_credits.credits.get(decision.credit_id)
    credit.credit_decision = decision
    credit.credit_payment = RecurringCreditPayment(
        monthly_amount=credit.credit_request.credit_amount
        / credit.credit_request.credit_duration_months,
        months_left=credit.credit_request.credit_duration_months,
    )
    ctx.set(CREDITS, all_credits)

    await notify_customer(
        ctx,
        f"Credit {decision.credit_id} was {'approved' if decision.approved else 'rejected'} for the reason: {decision.reason}",
    )


@account.handler()
async def on_recurring_credit_payment(ctx: restate.ObjectContext, credit_id: str):
    """
    Handle a scheduled payment for a credit.

    Args:
        credit_id (str): The ID of the credit.
    """
    all_credits = await get_customer_credits(ctx)
    credit = all_credits.credits.get(credit_id)

    # Do the transfer back to the bank
    transaction = Transaction(
        reason=f"credit payment {credit_id}",
        amount=credit.monthly_amount,
        timestamp=await time_now_string(ctx),
    )
    await withdraw(ctx, transaction)
    ctx.object_send(deposit, key="TrustworthyBank", arg=transaction)

    # If the credit is paid off, return
    if credit.months_left == 1:
        return

    # Otherwise, schedule the next payment
    credit.credit_payment = RecurringCreditPayment(
        monthly_amount=credit.monthly_amount, months_left=credit.months_left - 1
    )
    ctx.set(CREDITS, all_credits)

    ctx.object_send(
        on_recurring_credit_payment,
        key=ctx.key(),
        arg=credit_id,
        send_delay=timedelta(days=30),
    )


@account.handler()
async def get_customer_credits(ctx: restate.ObjectContext) -> CustomerCreditOverview:
    """
    Get the ongoing credit requests and credit payments for the customer.

    Returns:
        CustomerCreditOverview: The overview of the customer's outstanding credits and credit requests.
    """
    return (
        await ctx.get(CREDITS, type_hint=CustomerCreditOverview) or CustomerCreditOverview()
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
    from .chat import ChatMessage, add_async_response

    chat_message = ChatMessage(
        role="system",
        content=message,
        timestamp_millis=await time_now(ctx),
    )
    ctx.object_send(add_async_response, key=ctx.key(), arg=chat_message)
