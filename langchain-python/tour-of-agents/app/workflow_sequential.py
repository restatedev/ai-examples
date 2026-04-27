"""Sequential pipeline: parse → analyze → currency conversion → payment.
Each step is durable, so the workflow can resume mid-pipeline after a
failure without re-running already-completed steps."""

import restate
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model

from restate.ext.langchain import RestateMiddleware

from utils.models import ClaimData, ClaimPrompt
from utils.utils import convert_currency, process_payment


# <start_here>
claim_service = restate.Service("ClaimReimbursement")


@claim_service.handler()
async def process(ctx: restate.Context, req: ClaimPrompt) -> dict:
    # Step 1: Parse the claim document (structured-output LLM step).
    parse_agent = create_agent(
        model=init_chat_model("openai:gpt-4o-mini"),
        tools=[],
        system_prompt="Extract the claim amount, currency, category, and description.",
        response_format=ClaimData,
        middleware=[RestateMiddleware()],
    )
    parsed = await parse_agent.ainvoke(
        {"messages": [{"role": "user", "content": req.message}]}
    )
    claim: ClaimData = ClaimData.model_validate(parsed["structured_response"])

    # Step 2: Analyze the claim (LLM step).
    analysis_agent = create_agent(
        model=init_chat_model("openai:gpt-4o-mini"),
        tools=[],
        system_prompt="Assess whether this claim is valid and determine the approved amount.",
        middleware=[RestateMiddleware()],
    )
    analysis = await analysis_agent.ainvoke(
        {"messages": [{"role": "user", "content": f"Claim: {claim.model_dump_json()}"}]}
    )

    # Step 3: Convert currency (regular durable step).
    amount_usd = await ctx.run_typed(
        "Convert currency",
        convert_currency,
        amount=claim.amount,
        source=claim.currency,
        target="USD",
    )

    # Step 4: Process reimbursement (regular durable step).
    confirmation = await ctx.run_typed(
        "Process payment",
        process_payment,
        claim_id=str(ctx.uuid()),
        amount=amount_usd,
    )

    return {
        "analysis": analysis["messages"][-1].content,
        "amount_usd": amount_usd,
        "confirmation": confirmation,
    }


# <end_here>


if __name__ == "__main__":
    import asyncio

    import hypercorn
    import hypercorn.asyncio

    app = restate.app(services=[claim_service])
    conf = hypercorn.Config()
    conf.bind = ["0.0.0.0:9080"]
    asyncio.run(hypercorn.asyncio.serve(app, conf))
