# UTILS


async def update_seat_in_booking_system(
    confirmation_number: str, new_seat: str, flight: dict[str, str]
) -> bool:
    # Simulate updating the seat in a booking system
    # In a real application, this would involve an API call or database update
    print(
        f"Updating seat for confirmation number {confirmation_number} and flight {flight} to {new_seat}"
    )
    return True


async def retrieve_flight_info(confirmation_number: str) -> dict:
    print(f"Looking up flight info related to {confirmation_number}")
    return {
        "flight_number": "AA123",
        "departure": "2023-10-01T10:00:00Z",
        "arrival": "2023-10-01T12:00:00Z",
    }


async def send_invoice(confirmation_number: str, flight: dict[str, str]) -> str:
    print(
        f"Sending invoice for confirmation number {confirmation_number} and flight {flight}"
    )
    return f"Invoice sent for confirmation number {confirmation_number} and flight {flight}."
