import restate

invoice_sender = restate.Service("InvoiceSender")

@invoice_sender.handler()
async def send_invoice(ctx: restate.Context, passenger_name: str) -> None:
    """Send an invoice to a customer."""
    print(f"Sending invoice to {passenger_name}")
    # Send invoice logic here
    print("Invoice sent!")