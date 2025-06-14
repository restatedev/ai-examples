import logging
import restate

from openai import OpenAI

from utils.models import ClaimRequest, ClaimData
from utils.utils import (
    extract_text_from_pdf,
    check_missing_fields,
    send_message_to_customer,
    create_claim,
)

logger = logging.getLogger(__name__)

client = OpenAI()

claim_workflow = restate.Service("InsuranceClaimWorkflow")


@claim_workflow.handler()
async def run(ctx: restate.Context, req: ClaimRequest) -> ClaimData:
    """
    Resilient LLM-based insurance claim workflow that processes a PDF receipt and extracts claim data.
    It checks for missing fields and requests additional information from the customer if needed.
    """

    # Parse the PDF receipt
    raw_claim = await ctx.run("Read PDF", extract_text_from_pdf, args=(req.url,))

    def parse_claim_data(extra_info: str = "") -> ClaimData:
        return client.responses.parse(
            model="gpt-4o-2024-08-06",
            input=[
                {"role": "system", "content": "Extract the claim information."},
                {
                    "role": "user",
                    "content": f"Claim data: {raw_claim}  Extra info: {extra_info}",
                },
            ],
            text_format=ClaimData,
        ).output_parsed

    # Extract claim data
    claim = await ctx.run("Extracting", parse_claim_data, args=())

    # Repetitively check for missing fields and request additional information if needed
    while True:
        missing_fields = await ctx.run(
            "completeness check", lambda last_claim=claim: check_missing_fields(last_claim))
        if not missing_fields:
            break

        id, promise = ctx.awakeable()
        await ctx.run(
            "Request missing info", lambda last_id=id: send_message_to_customer(missing_fields, last_id)
        )
        extra_info = await promise
        claim = await ctx.run("Extracting", lambda new_info=extra_info: parse_claim_data(new_info), type_hint=ClaimData)

    # Create the claim in the legacy system
    await ctx.run("create", lambda last_claim=claim: create_claim(last_claim))
    return claim
