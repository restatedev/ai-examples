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
    return f"Invoice sent to {req.passenger_name} at {req.passenger_email}"