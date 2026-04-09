# MODELS
from typing import AsyncGenerator
from google.adk.events import Event
from pydantic import BaseModel


class ClaimDocument(BaseModel):
    text: str = (
        "Hospital bill for broken leg treatment at General Hospital for 3000 euro on 24/04/26"
    )


class ClaimData(BaseModel):
    """Insurance claim data structure."""

    date: str
    amount: float
    currency: str
    reason: str


class ClaimAssessment(BaseModel):
    """Claim assessment result."""

    valid: bool
    reasoning: str


async def query_fraud_db(claim_id: str) -> dict[str, str]:
    return {"risk_score": "0.12"}


async def convert_currency(amount: float) -> float:
    return amount * 0.92  # USD to EUR


async def reimburse(amount: float) -> str:
    return "Reimbursed"


async def parse_agent_response(events: AsyncGenerator[Event, None]) -> str:
    """Run an ADK agent and return the final text response."""
    final_response = ""
    async for event in events:
        if event.is_final_response() and event.content and event.content.parts:
            if event.content.parts[0].text:
                final_response = event.content.parts[0].text
    return final_response