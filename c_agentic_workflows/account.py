import restate

from utils.pydantic_models import (
    Transaction,
    TransactionHistory,
    CustomerLoanOverview,
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
