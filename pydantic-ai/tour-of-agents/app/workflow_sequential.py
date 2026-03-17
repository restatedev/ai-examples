import restate
from pydantic_ai import Agent
from restate.ext.pydantic import RestateAgent
from utils.models import ClaimPrompt, ClaimData
from utils.utils import convert_currency, process_payment

# <start_here>
parse_agent = Agent(
    "openai:gpt-4o-mini",
    system_prompt="Extract the claim amount, currency, category, and description.",
    output_type=ClaimData,
)
restate_parse_agent = RestateAgent(parse_agent)

analysis_agent = Agent(
    "openai:gpt-4o-mini",
    system_prompt="Analyze the claim and approve/deny it.",
    output_type=bool,
)
restate_analysis_agent = RestateAgent(analysis_agent)

claim_service = restate.Service("ClaimReimbursement")


@claim_service.handler()
async def process(ctx: restate.Context, req: ClaimPrompt) -> dict:
    # Step 1: Parse the claim document (LLM step)
    parsed = await restate_parse_agent.run(req.message)
    claim = parsed.output

    # Step 2: Analyze the claim (LLM step)
    approved = await restate_analysis_agent.run(f"Claim: {claim.model_dump_json()}")
    if not approved.output:
        return {"analysis": "Claim is invalid", "amountUsd": 0, "confirmation": False}

    # Step 3: Convert currency (regular step)
    amount_usd = await ctx.run_typed(
        "Convert currency",
        convert_currency,
        amount=claim.amount,
        source=claim.currency,
        target="USD",
    )

    # Step 4: Process reimbursement (regular step)
    confirmation = await ctx.run_typed(
        "Process payment",
        process_payment,
        claim_id=str(ctx.uuid()),
        amount=amount_usd,
    )

    return {
        "analysis": "Claim is valid.",
        "amount_usd": amount_usd,
        "confirmation": confirmation,
    }


# <end_here>


if __name__ == "__main__":
    import hypercorn
    import asyncio

    app = restate.app(services=[claim_service])
    conf = hypercorn.Config()
    conf.bind = ["0.0.0.0:9080"]
    asyncio.run(hypercorn.asyncio.serve(app, conf))
