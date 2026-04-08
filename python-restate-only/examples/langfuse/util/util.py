from typing import Any
from pydantic import BaseModel


class ClaimPrompt(BaseModel):
    message: str = (
        "Process my hospital bill of 2024-10-01 for 3000USD for a broken leg at General Hospital."
    )


class ClaimData(BaseModel):
    """Insurance claim data structure."""

    date: str
    amount: float
    currency: str
    reason: str


class ClaimEvaluation(BaseModel):
    """Evaluation of an insurance claim."""

    valid: bool


async def convert_currency(amount: float, source: str, target: str) -> float:
    """Convert between currencies using mock exchange rates."""
    return amount * 1.3


async def process_payment(claim_id: str, amount: float) -> str:
    """Process a reimbursement payment (mock)."""
    return f"Payment of ${amount:.2f} USD. Reference: PAY-123"
