import restate
from google.adk.agents.llm_agent import Agent
from google.adk import Runner
from google.adk.apps import App
from google.genai.types import Content, Part
from restate.ext.adk import RestatePlugin, restate_context, RestateSessionService

from utils.utils import (
    ClaimData,
    ClaimAssessment,
    ClaimDocument,
    convert_currency,
    reimburse,
    query_fraud_db, parse_agent_response,
)


# TOOLS
async def check_fraud_database(customer_id: str) -> dict:
    """Check the claim against the fraud database."""
    return await restate_context().run_typed(
        "Query fraud DB", query_fraud_db, claim_id=customer_id
    )


# AGENTS
parse_agent = Agent(
    model="gemini-2.5-flash",
    name="DocumentParser",
    instruction="Extract the claim amount, currency, category, and description.",
    output_schema=ClaimData,
)
parse_app = App(name="parse", root_agent=parse_agent, plugins=[RestatePlugin()])
parse_runner = Runner(app=parse_app, session_service=RestateSessionService())

analysis_agent = Agent(
    model="gemini-2.5-flash",
    name="ClaimsAnalyst",
    instruction="Assess whether this claim is valid and provide detailed reasoning.",
    output_schema=ClaimAssessment,
    tools=[check_fraud_database],
)
analysis_app = App(name="analysis", root_agent=analysis_agent, plugins=[RestatePlugin()])
analysis_runner = Runner(app=analysis_app, session_service=RestateSessionService())

claim_service = restate.VirtualObject("ClaimReimbursement")


# MAIN ORCHESTRATOR
claim_service = restate.VirtualObject("InsuranceClaimAgent")


@claim_service.handler()
async def run(ctx: restate.ObjectContext, req: ClaimDocument) -> str:
    # Step 1: Parse the claim document (LLM step)
    parsing_events = parse_runner.run_async(
        user_id=ctx.key(),
        session_id=str(ctx.uuid()),
        new_message=Content(role="user", parts=[Part.from_text(text=req.text)]),
    )
    parsed = await parse_agent_response(parsing_events)
    claim = ClaimData.model_validate_json(parsed)

    # Step 2: Analyze the claim (LLM step)
    analysis_events = analysis_runner.run_async(
        user_id=ctx.key(),
        session_id=str(ctx.uuid()),
        new_message=Content(role="user", parts=[Part.from_text(text=parsed)]),
    )
    analysis = await parse_agent_response(analysis_events)
    assessment = ClaimAssessment.model_validate_json(analysis)

    if not assessment.valid:
        return "Claim rejected"

    # Step 3: Convert currency (regular durable step, no LLM)
    converted = await ctx.run_typed(
        "Convert currency", convert_currency, amount=claim.amount
    )

    # Step 4: Process reimbursement (regular durable step, no LLM)
    await ctx.run_typed("Reimburse", reimburse, amount=converted)

    return "Claim reimbursed"
