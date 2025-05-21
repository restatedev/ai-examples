from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field
from restate.serde import PydanticJsonSerde


# ------------ CHAT MODELS ------------


class ChatMessage(BaseModel):
    """
    A chat message object.

    Attributes:
        role (str): The role of the sender (user, assistant, system).
        content (str): The message to send.
        timestamp_millis (int): The timestamp of the message in millis.
        timestamp (str): The timestamp of the message in YYYY-MM-DD format.
    """

    role: str
    content: str


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
    timestamp_millis: int = Field(
        default_factory=lambda data: int(
            datetime.strptime(data["timestamp"], "%Y-%m-%d").timestamp() * 1000
        )
    )


class TransactionHistory(BaseModel):
    transactions: list[Transaction]


TransactionCategory = Literal[
    "income",
    "credit_payment",
    "gambling",
    "payday_credit",
    "cash_withdrawal",
    "basic_expense",
    "other",
]


class EnrichedTransaction(BaseModel):
    """
    A single transaction in a customer account.

    Attributes:
        amount (float): The amount of the transaction. Negative for expenses, positive for income
        category (TransactionCategory): The category of the transaction.  # e.g., "income", "credit_payment", "gambling", etc.
        timestamp (str): The timestamp of the transaction in YYYY-MM-DD format
        reason (str): The reason for the transaction. This is a free-form string that describes the transaction.
    """

    amount: float
    category: TransactionCategory
    timestamp: str
    reason: str


class EnrichedTransactionHistory(BaseModel):
    """
    A customer account's transaction history enriched with categories.

    Attributes:
        transactions (list[Transaction]): A list of transactions
    """

    transactions: list[EnrichedTransaction]


# ------------ CREDIT MODELS ------------


class RecurringCreditPayment(BaseModel):
    monthly_amount: float
    months_left: int


class CreditRequest(BaseModel):
    """
    A credit request object.

    Attributes:
        customer_id (str): The customer ID who requested the credit.
        credit_amount (int): The amount of the credit.
        credit_duration_months (int): The duration of the credit in months.
    """

    customer_id: str
    credit_amount: int
    credit_duration_months: int


class CreditReviewRequest(BaseModel):
    """
    A credit request object.

    Attributes:
        credit_request (CreditRequest): the credit request itself
        transaction_history (TransactionHistory): The transaction history of the customer
    """

    credit_request: CreditRequest
    transaction_history: TransactionHistory


class CreditStatus(BaseModel):
    """
    A credit status object.

    Attributes:
        events (list[str]): The events that happened during the credit approval process.
    """

    events: list[str] = Field(default_factory=list)


class CreditDecision(BaseModel):
    """
    A credit decision object.

    Attributes:
        credit_id (str): The ID of the credit.
        approved (bool): Whether the credit was approved or not.
        reason (str): The reason for the decision.
    """

    credit_id: str
    approved: bool
    reason: str


CreditDecisionSerde = PydanticJsonSerde(CreditDecision)


class Credit(BaseModel):
    """
    A credit object.

    Attributes:
        credit_id (str): The ID of the credit.
        credit_request (CreditRequest): The initial credit request.
        credit_decision (CreditDecision): Information about whether the credit was approved or not, and the reason.
        credit_payment (RecurringCreditPayment): Information about the monthly credit payment and remaining duration.
    """

    credit_id: str
    credit_request: CreditRequest
    credit_decision: CreditDecision | None = Field(default=None)
    credit_payment: RecurringCreditPayment | None = Field(default=None)


class CustomerCreditOverview(BaseModel):
    """
    The ongoing credit requests and credit payments for the customer.

    Attributes:
        credits (Dict[str, Credit]): The list of credits.
    """

    credits: dict[str, Credit] = Field(default_factory=dict)


# ------------ CREDIT WORTHINESS MODELS ------------


class CreditMetric(BaseModel):
    """
    The result of a credit worthiness metric.

    Attributes:
        value (float): The value of the outcome
        label (str): The name of the metric
    """

    label: str
    value: float


class CreditMetricList(BaseModel):
    """
    A list of credit worthiness outcomes.

    Attributes:
        metrics (List[CreditMetric]): A list of credit worthiness outcomes
    """

    metrics: list[CreditMetric]


class AdditionalInfoRequest(BaseModel):
    """
    A message to the customer to request additional information.

    Args:
        customer_id (str): The customer ID.
        message (str): The message to send.
    """

    customer_id: str
    message: str
