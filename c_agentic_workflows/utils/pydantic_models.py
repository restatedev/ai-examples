from typing import Dict, List, Literal

from pydantic import BaseModel, Field
from restate.serde import PydanticJsonSerde


# ------------ CHAT MODELS ------------


class ChatMessage(BaseModel):
    """
    A chat message object.

    Attributes:
        role (str): The role of the sender (user, assistant, system).
        content (str): The message to send.
        timestamp (int): The timestamp of the message in millis.
    """

    role: str
    content: str
    timestamp: int


class ChatHistory(BaseModel):
    """
    A chat history object.

    Attributes:
        entries (list[ChatMessage]): The list of chat messages.
    """

    entries: list[ChatMessage] = Field(default_factory=list)


# ------------ TRANSACTION MODELS ------------


class Transaction(BaseModel):
    reason: str
    amount: float
    timestamp: str


class TransactionHistory(BaseModel):
    transactions: list[Transaction]


# ------------ LOAN MODELS ------------


class RecurringLoanPayment(BaseModel):
    monthly_amount: float
    months_left: int


class LoanRequest(BaseModel):
    """
    A loan request object.

    Attributes:
        customer_id (str): The customer ID who requested the loan.
        loan_amount (int): The amount of the loan.
        loan_duration_months (int): The duration of the loan in months.
    """

    customer_id: str
    loan_amount: int
    loan_duration_months: int


class LoanDecision(BaseModel):
    """
    A loan decision object.

    Attributes:
        loan_id (str): The ID of the loan.
        approved (bool): Whether the loan was approved or not.
        reason (str): The reason for the decision.
    """

    loan_id: str
    approved: bool
    reason: str


LoanDecisionSerde = PydanticJsonSerde(LoanDecision)


class Loan(BaseModel):
    """
    A loan object.

    Attributes:
        loan_id (str): The ID of the loan.
        loan_request (LoanRequest): The initial loan request.
        loan_decision (LoanDecision): Information about whether the loan was approved or not, and the reason.
        loan_payment (RecurringLoanPayment): Information about the monthly loan payment and remaining duration.
    """

    loan_id: str
    loan_request: LoanRequest
    loan_decision: LoanDecision | None = Field(default=None)
    loan_payment: RecurringLoanPayment | None = Field(default=None)


class CustomerLoanOverview(BaseModel):
    """
    The ongoing loan requests and loan payments for the customer.

    Attributes:
        loans (Dict[str, Loan]): The list of loans.
    """

    loans: Dict[str, Loan] = Field(default={})
