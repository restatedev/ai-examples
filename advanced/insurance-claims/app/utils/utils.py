import logging
import uuid

from pypdf import PdfReader

from .models import ClaimData

logger = logging.getLogger(__name__)


def extract_text_from_pdf(url: str) -> str:
    logger.info("Parsing PDF receipt for claim")
    pdf_reader = PdfReader(url)
    text = ""
    for page_num in range(len(pdf_reader.pages)):
        text += pdf_reader.pages[page_num].extract_text()
    return text


def create_claim(claim: ClaimData) -> str:
    # Simulate creating a claim in a legacy system
    # In a real-world scenario, this would involve making an API call to the legacy system
    # and returning the assigned claim ID.
    logger.info("Creating claim in legacy system: %s", claim.model_dump_json())
    return uuid.uuid4().hex


def send_message_to_customer(missing_fields: list[str], id: str) -> None:
    print(
        "=" * 50,
        f"\n Requesting more info for claim \n",
        f"The following information is missing: {missing_fields}. Please provide the information as follows:\n",
        f"curl localhost:8080/restate/awakeables/{id}/resolve --json '\"Your message\"' \n",
        "=" * 50,
    )


def check_missing_fields(claim_data: ClaimData) -> list[str]:
    # Check if all required fields are present in the claim data
    required_fields = ClaimData.model_fields.keys()
    missing_fields = []
    for field in required_fields:
        if getattr(claim_data, field) is None:
            missing_fields.append(field)

    if missing_fields:
        logger.info("The following fields are missing: %s", missing_fields)
    return missing_fields
