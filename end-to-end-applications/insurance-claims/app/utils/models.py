from enum import Enum
from pydantic import BaseModel


class ClaimRequest(BaseModel):
    """
    A request to process a medical expense receipt.

    Attributes:
        user_id (str): The user ID of the person making the claim.
        url (str): The URL of the PDF file containing the claim information.
    """

    user_id: str
    url: str


class ClaimCategory(str, Enum):
    DENTAL = "dental"
    MEDICAL = "medical"
    VISION = "vision"
    PRESCRIPTION = "prescription"
    CHIROPRACTIC = "chiropractic"
    MENTAL_HEALTH = "mental_health"
    OTHER = "other"


class ClaimData(BaseModel):
    """
    Data model for the claim data.
    This model is used to store the information extracted from the claim PDF.

    Attributes:
        date (str): The date of the claim in YYYY-MM-DD format.
        amount (float): The amount of the claim.
        description (str): A description of the claim.
        category (ClaimCategory): The category of the claim.
        place_of_service (str): The place where the service was provided: Name of Doctor, Clinic, etc.
    """

    date: str | None = None
    amount: float | None = None
    description: str | None = None
    category: ClaimCategory | None = None
    place_of_service: str | None = None
