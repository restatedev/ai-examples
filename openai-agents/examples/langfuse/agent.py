import restate
from pydantic import BaseModel
from agents import Agent
from restate.ext.openai import restate_context, DurableRunner, durable_function_tool

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class ClaimRequest(BaseModel):
    claim_id: str = "CLM-2024-001"
    amount: float = 3000.0
    description: str = "Hospital bill for broken leg treatment at General Hospital"


# ---------------------------------------------------------------------------
# Tool – fraud database check (used by the parser agent)
# ---------------------------------------------------------------------------

@durable_function_tool
async def check_fraud_database(claim_id: str) -> dict[str, str]:
    """Check the claim against the fraud database."""
    async def _check(claim_id: str) -> dict[str, str]:
        return { "risk_score": "0.12"}
    return await restate_context().run_typed("Check fraud DB", _check, claim_id=claim_id)

# ---------------------------------------------------------------------------
# Agent definitions
# ---------------------------------------------------------------------------

parser_agent = Agent(
    name="ClaimParserAgent",
    instructions="You are a claim intake specialist. Parse the insurance claim, "
        "extract key information, and check the fraud database. "
        "Provide a structured summary of the claim with the fraud check results.",
    tools=[check_fraud_database],
)

analysis_agent = Agent(
    name="ClaimAnalysisAgent",
    instructions="You are a claims analyst. Based on the parsed claim data, "
        "determine if the claim is eligible for reimbursement. "
        "Check policy validity, coverage limits, and provide your assessment.",
    output_type=bool,
)

# ---------------------------------------------------------------------------
# Main orchestrator – the insurance claim workflow
# ---------------------------------------------------------------------------

claim_service = restate.Service("InsuranceClaimAgent")

@claim_service.handler()
async def run(ctx: restate.Context, claim: ClaimRequest) -> str:
    # Step 1: Parse claim documents with LLM agent
    parsed = await DurableRunner.run(
        parser_agent,
        f"Parse this insurance claim: {claim.model_dump_json()}",
    )

    # Step 2: Analyze claim eligibility with LLM agent
    analysis = await DurableRunner.run(
        analysis_agent,
        f"Analyze this claim for eligibility:\n{parsed.final_output}",
    )
    eligible = analysis.final_output

    if eligible:
        # Step 3: Convert currency (regular durable step, no LLM)
        async def convert_currency(amount: float) -> float:
            return amount * 0.92  # USD to EUR
        converted = await ctx.run_typed("Convert currency", convert_currency, amount=claim.amount)

        # Step 4: Process reimbursement (regular durable step, no LLM)
        async def reimburse(claim_id: str, amount: float) -> str:
            return f"Reimbursed €{amount:.2f} for claim {claim_id}"
        await ctx.run_typed("Process reimbursement", reimburse, claim_id=claim.claim_id, amount=converted)

    return f"Claim {claim.claim_id} {"reimbursed" if eligible else "rejected"}"
