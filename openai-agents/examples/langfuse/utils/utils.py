# MODELS
from restate import TerminalError
from pydantic import BaseModel


class ClaimDocument(BaseModel):
    text: str = (
        "Customer ID: cus_123 - Hospital bill for broken leg treatment at General Hospital for 3000 euro on 24/04/26"
    )


class ClaimData(BaseModel):
    """Insurance claim data structure."""

    customer_id: str
    date: str
    amount: float
    currency: str
    reason: str


class ClaimAssessment(BaseModel):
    """Claim assessment result."""

    valid: bool
    reasoning: str


class EvaluationRequest(BaseModel):
    traceparent: str
    input: str
    output: str

    def trace_id(self) -> str:
        """Extract the OTel trace ID from the W3C traceparent."""
        if not self.traceparent:
            raise TerminalError(
                "No traceparent header found. Is Restate tracing enabled?"
            )
        return self.traceparent.split("-")[1]


class EvaluationScore(BaseModel):
    score: float
    reason: str


async def query_fraud_db(claim_id: str) -> dict[str, str]:
    return {"risk_score": "0.12"}


async def convert_currency(amount: float) -> float:
    return amount * 0.92  # USD to EUR


async def reimburse(amount: float) -> str:
    return "Reimbursed"
