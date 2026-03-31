import restate
from google.adk.agents.llm_agent import Agent
from google.adk import Runner
from google.adk.apps import App
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, Part
from restate.ext.adk import RestatePlugin, restate_context

from utils.utils import (
    ClaimData,
    ClaimAssessment,
    ClaimDocument,
    convert_currency,
    reimburse,
    query_fraud_db,
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
    instruction="Extract the customer ID, claim amount, currency, category, and description.",
    output_schema=ClaimData,
)

analysis_agent = Agent(
    model="gemini-2.5-flash",
    name="ClaimsAnalyst",
    instruction="Assess whether this claim is valid and provide detailed reasoning.",
    output_schema=ClaimAssessment,
    tools=[check_fraud_database],
)

# APPS
PARSE_APP = "parse"
parse_app = App(name=PARSE_APP, root_agent=parse_agent, plugins=[RestatePlugin()])
parse_sessions = InMemorySessionService()

ANALYSIS_APP = "analysis"
analysis_app = App(name=ANALYSIS_APP, root_agent=analysis_agent, plugins=[RestatePlugin()])
analysis_sessions = InMemorySessionService()


async def run_agent(app, app_name, session_service, ctx, message: str) -> str:
    """Run an ADK agent and return the final text response."""
    user_id = "system"
    session_id = str(ctx.uuid())

    session = await session_service.get_session(
        app_name=app_name, user_id=user_id, session_id=session_id
    )
    if not session:
        await session_service.create_session(
            app_name=app_name, user_id=user_id, session_id=session_id
        )

    runner = Runner(app=app, session_service=session_service)
    events = runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=Content(role="user", parts=[Part.from_text(text=message)]),
    )

    final_response = None
    async for event in events:
        if event.is_final_response() and event.content and event.content.parts:
            if event.content.parts[0].text:
                final_response = event.content.parts[0].text
    return final_response


# MAIN ORCHESTRATOR
claim_service = restate.Service("InsuranceClaimAgent")


@claim_service.handler()
async def run(ctx: restate.Context, req: ClaimDocument) -> str:
    # Step 1: Parse the claim document (LLM step)
    parse_result = await run_agent(
        parse_app, PARSE_APP, parse_sessions, ctx, req.text
    )
    claim = ClaimData.model_validate_json(parse_result)

    # Step 2: Analyze the claim (LLM step)
    analysis_result = await run_agent(
        analysis_app, ANALYSIS_APP, analysis_sessions, ctx, claim.model_dump_json()
    )
    assessment = ClaimAssessment.model_validate_json(analysis_result)

    if not assessment.valid:
        return "Claim rejected"

    # Step 3: Convert currency (regular durable step, no LLM)
    converted = await ctx.run_typed(
        "Convert currency", convert_currency, amount=claim.amount
    )

    # Step 4: Process reimbursement (regular durable step, no LLM)
    await ctx.run_typed("Reimburse", reimburse, amount=converted)

    return "Claim reimbursed"