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
    raw_claim = await ctx.run_typed("Read PDF", extract_text_from_pdf, url=req.url)

    def parse_claim_data(raw_claim_input: str, extra_info_input: str = "") -> ClaimData:
        return (
            client.responses.parse(
                model="gpt-4o-2024-08-06",
                input=[
                    {"role": "system", "content": "Extract the claim information."},
                    {
                        "role": "user",
                        "content": f"Claim data: {raw_claim_input}  Extra info: {extra_info_input}",
                    },
                ],
                text_format=ClaimData,
            ).output_parsed
            or ClaimData()
        )

    # Extract claim data
    claim = await ctx.run_typed(
        "Extracting",
        parse_claim_data,
        restate.RunOptions(type_hint=ClaimData),
        raw_claim_input=raw_claim,
    )

    # Repetitively check for missing fields and request additional information if needed
    while True:
        missing_fields = await ctx.run_typed(
            "completeness check", check_missing_fields, claim=claim
        )
        if not missing_fields:
            break

        id, promise = ctx.awakeable(type_hint=str)
        await ctx.run_typed(
            "Request missing info",
            send_message_to_customer,
            missing_fields=missing_fields,
            id=id,
        )
        extra_info = await promise

        claim = await ctx.run_typed(
            "Extracting",
            parse_claim_data,
            restate.RunOptions(type_hint=ClaimData),
            raw_claim_input=raw_claim,
            extra_info_input=extra_info,
        )

    # Create the claim in the legacy system
    await ctx.run_typed("create", lambda: create_claim(claim))
    return claim
