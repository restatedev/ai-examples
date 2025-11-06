import calendar
from datetime import timedelta, datetime

import restate
from pydantic import BaseModel

class Reimbursement(BaseModel):
    """
    A request for reimbursement.

    Args:
        request_id (str): The ID of the request.
        date (str): The date of the request.
        amount (float): The requested amount in USD.
        purpose (str): The purpose of the request.
    """

    request_id: str
    date: str
    amount: float
    purpose: str


def backoffice_submit_request(request_id: str, callback_id: str) -> None:
    print(
        "=" * 50,
        f"\n Requesting approval for {request_id} \n",
        f"Resolve via: \n"
        f"curl localhost:8080/restate/awakeables/{callback_id}/resolve --json '{{\"approved\": true}}' \n",
        "=" * 50,
    )


def backoffice_email_employee(request_id: str, approved: bool) -> None:
    print("Notifying backoffice employee of reimbursement approval")


def end_of_month(time_now: float) -> timedelta:
    now = datetime.fromtimestamp(time_now)
    last_day = calendar.monthrange(now.year, now.month)[1]
    end_of_month_datetime = datetime(now.year, now.month, last_day, 23, 59, 59, 999999)

    time_remaining = end_of_month_datetime - now
    return timedelta(seconds=time_remaining.total_seconds())


payment_service = restate.Service("PaymentService")

@payment_service.handler()
async def handle_payment(ctx: restate.ObjectContext, req: Reimbursement):
    print(f"Processing reimbursement payment for request ID: {req.request_id}, Amount: {req.amount}")
    # Here you would integrate with your payment processing system
    # For this example, we'll just log the payment processing
    print(f"Reimbursement of ${req.amount} for request ID: {req.request_id} has been processed.")