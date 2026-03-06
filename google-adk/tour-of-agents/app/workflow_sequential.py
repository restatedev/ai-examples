import restate
from google.adk import Runner
from google.adk.agents.llm_agent import Agent
from google.adk.apps import App
from google.genai.types import Content, Part
from restate.ext.adk import RestatePlugin, RestateSessionService
from utils.models import ClaimData, ClaimPrompt
from utils.utils import parse_agent_response, convert_currency, process_payment


# <start_here>
parse_agent = Agent(
    model="gemini-2.5-flash",
    name="document_parser",
    instruction="Extract the claim amount, currency, category, and description.",
    output_schema=ClaimData
)
parse_app = App(name="claims", root_agent=parse_agent, plugins=[RestatePlugin()])
parse_runner = Runner(app=parse_app, session_service=RestateSessionService())

analysis_agent = Agent(
    model="gemini-2.5-flash",
    name="claims_analyst",
    instruction="Assess whether this claim is valid and determine the approved amount.",
)
analysis_app = App(name="claims", root_agent=analysis_agent, plugins=[RestatePlugin()])
analysis_runner = Runner(app=analysis_app, session_service=RestateSessionService())

claim_service = restate.VirtualObject("ClaimReimbursement")


@claim_service.handler()
async def process(ctx: restate.ObjectContext, req: ClaimPrompt) -> dict:
    # Step 1: Parse the claim document (LLM step)
    parsing_events = parse_runner.run_async(
        user_id=req.user_id,
        session_id=req.session_id,
        new_message=Content(role="user", parts=[Part.from_text(text=req.message)]),
    )
    parsed = await parse_agent_response(parsing_events)
    claim = ClaimData.model_validate_json(parsed)

    # Step 2: Analyze the claim (LLM step)
    analysis_events = analysis_runner.run_async(
        user_id=req.user_id,
        session_id=req.session_id,
        new_message=Content(role="user", parts=[Part.from_text(text=parsed)]),
    )
    analysis = await parse_agent_response(analysis_events)

    # Step 3: Convert currency (regular step)
    amount_usd = await ctx.run_typed(
        "Convert currency", convert_currency,
        amount=claim.amount, source=claim.currency, target="USD",
    )

    # Step 4: Process reimbursement (regular step)
    confirmation = await ctx.run_typed(
        "Process payment", process_payment,
        claim_id=str(ctx.uuid()), amount=amount_usd,
    )

    return {"analysis": analysis, "amount_usd": amount_usd, "confirmation": confirmation}
# <end_here>


if __name__ == "__main__":
    import hypercorn
    import asyncio

    restate_app = restate.app(services=[claim_service])
    conf = hypercorn.Config()
    conf.bind = ["0.0.0.0:9080"]
    asyncio.run(hypercorn.asyncio.serve(restate_app, conf))
