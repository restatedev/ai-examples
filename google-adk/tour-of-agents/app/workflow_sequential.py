import json

import restate
from google.adk import Runner
from google.adk.agents.llm_agent import Agent
from google.adk.apps import App
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, Part
from pydantic import BaseModel
from restate.ext.adk import RestatePlugin


class ClaimRequest(BaseModel):
    user_id: str = "user-123"
    document: str = ""
    claim_id: str = ""


async def convert_currency(amount: float, source: str, target: str) -> float:
    """Convert currency (placeholder)."""
    return amount


async def process_payment(claim_id: str, amount: float) -> str:
    """Process payment (placeholder)."""
    return f"Payment processed for claim {claim_id}: ${amount}"


async def run_agent(runner: Runner, user_id: str, session_id: str, message: str) -> str:
    """Run an ADK agent and return the final text response."""
    events = runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=Content(role="user", parts=[Part.from_text(text=message)]),
    )
    final_response = ""
    async for event in events:
        if event.is_final_response() and event.content and event.content.parts:
            if event.content.parts[0].text:
                final_response = event.content.parts[0].text
    return final_response


# <start_here>
claim_service = restate.Service("ClaimReimbursement")


@claim_service.handler()
async def process(ctx: restate.Context, req: ClaimRequest) -> dict:
    # Step 1: Parse the claim document (LLM step)
    parse_agent = Agent(
        model="gemini-2.5-flash",
        name="document_parser",
        instruction="Extract the claim amount, currency, category, and description.",
    )
    app = App(name="claims", root_agent=parse_agent, plugins=[RestatePlugin()])
    runner = Runner(app=app, session_service=InMemorySessionService())

    parsed = await run_agent(runner, req.user_id, "parse", req.document)
    claim = json.loads(parsed)

    # Step 2: Analyze the claim (LLM step)
    analysis_agent = Agent(
        model="gemini-2.5-flash",
        name="claims_analyst",
        instruction="Assess whether this claim is valid and determine the approved amount.",
    )
    app = App(name="claims", root_agent=analysis_agent, plugins=[RestatePlugin()])
    runner = Runner(app=app, session_service=InMemorySessionService())

    analysis = await run_agent(runner, req.user_id, "analyze", f"Claim: {parsed}")

    # Step 3: Convert currency (regular step)
    amount_usd = await ctx.run_typed(
        "Convert currency", convert_currency,
        amount=claim["amount"], source=claim["currency"], target="USD",
    )

    # Step 4: Process reimbursement (regular step)
    confirmation = await ctx.run_typed(
        "Process payment", process_payment,
        claim_id=req.claim_id, amount=amount_usd,
    )

    return {"analysis": analysis, "amount_usd": amount_usd, "confirmation": confirmation}
# <end_here>


if __name__ == "__main__":
    import hypercorn
    import asyncio

    app = restate.app(services=[claim_service])
    conf = hypercorn.Config()
    conf.bind = ["0.0.0.0:9080"]
    asyncio.run(hypercorn.asyncio.serve(app, conf))
