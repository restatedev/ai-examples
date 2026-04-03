import typing
import httpx
import restate

from typing import Any, Coroutine
from litellm.types.utils import Choices, ModelResponse
from pydantic import BaseModel
from restate import TerminalError, RunOptions

from util.litellm_call import llm_call


class ClaimPrompt(BaseModel):
    message: str = (
        "Process my hospital bill of 2024-10-01 for 3000USD for a broken leg at General Hospital."
    )


class ClaimData(BaseModel):
    """Insurance claim data structure."""

    date: str = "2024-10-01"
    amount: float = 3000
    currency: str = "EUR"
    reason: str = "hospital bill for a broken leg"


class ClaimEvaluation(BaseModel):
    """Evaluation of an insurance claim."""

    valid: bool


def tool(name: str, description: str, parameters: dict[str, Any] | None = None):
    tool_def: dict[str, Any] = {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
        },
    }
    if parameters:
        tool_def["function"]["parameters"] = parameters
    return tool_def


def tool_result(tool_id: str, tool_name: str, output: str) -> dict:
    return {
        "role": "tool",
        "tool_call_id": tool_id,
        "name": tool_name,
        "content": output,
    }


async def convert_currency(amount: float, source: str, target: str) -> float:
    """Convert between currencies using mock exchange rates."""
    return amount * 1.3


async def process_payment(claim_id: str, amount: float) -> str:
    """Process a reimbursement payment (mock)."""
    return f"Payment of ${amount:.2f} USD. Reference: PAY-123"
