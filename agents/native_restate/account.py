import restate

from native_restate.utils.utils import generate_loan_overview
from utils.models import (
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
async def get_customer_loans(ctx: restate.ObjectContext) -> CustomerLoanOverview:
    """
    Get the ongoing loan requests and loan payments for the customer.

    Returns:
        CustomerLoanOverview: The overview of the customer's outstanding loans and loan requests.
    """
    loans = await ctx.get(LOANS, type_hint=CustomerLoanOverview)
    # If there are no loans, generate a demo loan overview
    if loans is None:
        # Generate a demo loan overview
        loans = await ctx.run(
            "generate loans",
            lambda: generate_loan_overview(),
            type_hint=CustomerLoanOverview,
        )
        ctx.set(LOANS, loans)
    return loans


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
    # If there is no transaction history, generate a demo transaction history
    history = await ctx.get(TRANSACTION_HISTORY, type_hint=TransactionHistory)
    if history is None:
        history = await ctx.run(
            "generate transactions",
            lambda: generate_transactions(),
            type_hint=TransactionHistory,
        )
        ctx.set(TRANSACTION_HISTORY, history)
    return history
