import restate
from agents import Agent
from restate.ext.openai import restate_context, DurableRunner, durable_function_tool

from evaluation import evaluate, EvaluationRequest
from utils.utils import (
    ClaimData,
    ClaimAssessment,
    ClaimDocument,
    convert_currency,
    reimburse,
    query_fraud_db,
)


# TOOLS
@durable_function_tool
async def check_fraud_database(customer_id: str) -> dict[str, str]:
    """Check the claim against the fraud database."""
    return await restate_context().run_typed(
        "Query fraud DB", query_fraud_db, claim_id=customer_id
    )


# AGENTS
parse_agent = Agent(
    name="DocumentParser",
    model="gpt-5.2",
    instructions="Extract the customer ID, claim amount, currency, category, and description.",
    output_type=ClaimData,
)

analysis_agent = Agent(
    name="ClaimsAnalyst",
    model="gpt-5.2",
    instructions="Assess whether this claim is valid and provide detailed reasoning.",
    output_type=ClaimAssessment,
    tools=[check_fraud_database]
)

# MAIN ORCHESTRATOR
claim_service = restate.Service("InsuranceClaimAgent")


@claim_service.handler()
async def run(ctx: restate.Context, req: ClaimDocument) -> str:
    # Step 1: Parse the claim document (LLM step)
    parsed = await DurableRunner.run(parse_agent, req.text)
    claim: ClaimData = parsed.final_output

    # Step 2: Analyze the claim (LLM step)
    response = await DurableRunner.run(analysis_agent, claim.model_dump_json())
    assessment: ClaimAssessment = response.final_output

    if not assessment.valid:
        return f"Claim rejected"

    # Step 3: Convert currency (regular durable step, no LLM)
    converted = await ctx.run_typed(
        "Convert currency", convert_currency, amount=claim.amount
    )

    # Step 4: Process reimbursement (regular durable step, no LLM)
    await ctx.run_typed("Reimburse", reimburse, amount=converted)

    # Step 5: Optionally, kick off async LLM-as-a-Judge evaluation (non-blocking).
    ctx.service_send(
        evaluate,
        arg=EvaluationRequest(
            traceparent=ctx.request().attempt_headers.get("traceparent", ""),
            input=claim.model_dump_json(),
            output=assessment.model_dump_json(),
        ),
    )

    return f"Claim reimbursed"
