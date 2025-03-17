from datetime import timedelta

import restate

from pydantic import BaseModel

invoice_sender_svc = restate.Service("InvoiceSender")

class SendInvoiceRequest(BaseModel):
    """
    A request to the invoice sender.
    This request is the input for the tool with name: send_invoice
    The passenger name is the name of the passenger to send the invoice to.
    The passenger email is the email of the passenger to send the invoice to.
    """
    passenger_name: str
    passenger_email: str

@invoice_sender_svc.handler()
async def send_invoice(ctx: restate.Context, req: SendInvoiceRequest) -> None:
    """Send an invoice to a customer."""
    print(f"Sending invoice to {req.passenger_name} at {req.passenger_email}")
    # Send invoice logic here
    print("Invoice sent!")


class DelayedSendInvoiceRequest(BaseModel):
    """
    A request to the schedule_invoice_sending handler.
    This request is the input for the tool with name: send_invoice_delayed
    The delay_millis is the delay in milliseconds before sending the invoice
    The passenger name is the name of the passenger to send the invoice to.
    The passenger email is the email of the passenger to send the invoice to.
    """
    delay_millis: int
    send_invoice_request: SendInvoiceRequest

@invoice_sender_svc.handler()
async def send_invoice_delayed(ctx: restate.Context, req: DelayedSendInvoiceRequest) -> str:
    """
    Schedules the sending of an invoice after a delay specified in milliseconds.

    Args:
        req: The request to schedule the sending of an invoice.
    """
    ctx.service_send(
        send_invoice,
        arg=req.send_invoice_request,
        send_delay=timedelta(milliseconds=req.delay_millis))
    return f"Scheduled invoice sending for {req.send_invoice_request.passenger_name} in {req.delay_millis} milliseconds."