import restate
from pydantic_ai import Agent, RunContext
from restate.ext.pydantic import RestateAgent, restate_context

from utils.utils import (
    ClaimData,
    ClaimAssessment,
    ClaimDocument,
    convert_currency,
    reimburse,
    query_fraud_db,
)


# AGENTS
parse_agent = Agent(
    "openai:gpt-4o-mini",
    system_prompt="Extract the customer ID, claim amount, currency, category, and description.",
    output_type=ClaimData,
)

analysis_agent = Agent(
    "openai:gpt-4o-mini",
    system_prompt="Assess whether this claim is valid and provide detailed reasoning.",
    output_type=ClaimAssessment,
)


# TOOLS
@analysis_agent.tool()
async def check_fraud_database(_run_ctx: RunContext[None], customer_id: str) -> dict:
    """Check the claim against the fraud database."""
    return await restate_context().run_typed(
        "Query fraud DB", query_fraud_db, claim_id=customer_id
    )


# RESTATE AGENT WRAPPERS
restate_parse_agent = RestateAgent(parse_agent)
restate_analysis_agent = RestateAgent(analysis_agent)

# MAIN ORCHESTRATOR
claim_service = restate.Service("InsuranceClaimAgent")


@claim_service.handler()
async def run(ctx: restate.Context, req: ClaimDocument) -> str:
    # Step 1: Parse the claim document (LLM step)
    parsed = await restate_parse_agent.run(req.text)
    claim: ClaimData = parsed.output

    # Step 2: Analyze the claim (LLM step)
    response = await restate_analysis_agent.run(claim.model_dump_json())
    assessment: ClaimAssessment = response.output

    if not assessment.valid:
        return "Claim rejected"

    # Step 3: Convert currency (regular durable step, no LLM)
    converted = await ctx.run_typed(
        "Convert currency", convert_currency, amount=claim.amount
    )

    # Step 4: Process reimbursement (regular durable step, no LLM)
    await ctx.run_typed("Reimburse", reimburse, amount=converted)

    return "Claim reimbursed"
