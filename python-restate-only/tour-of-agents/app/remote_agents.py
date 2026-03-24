"""
Agent Routing

Route customer questions to specialized AI agents based on their content.
Each routing decision is durable and can be retried if it fails.

Flow: Customer Question → Classifier → Specialized Agent → Response
"""

import restate

from pydantic import BaseModel
from restate import RunOptions

from util.util import tool, billing_agent_svc, account_agent_svc, product_agent_svc
from util.litellm_call import llm_call


# Customer's question
class Question(BaseModel):
    message: str = "I can't log into my account. Keep getting invalid password errors."

# <start_here>
remote_agent_router = restate.Service("RemoteAgentRouter")

# Classify the request
SPECIALISTS = {
    "BillingAgent": "Expert in payments, charges, and refunds",
    "AccountAgent": "Expert in login issues and security",
    "ProductAgent": "Expert in features and how-to guides",
}


@remote_agent_router.handler()
async def answer(ctx: restate.Context, question: Question) -> str | None:
    """Classify request and route to appropriate specialized agent."""

    # 1. First, decide if a specialist is needed
    routing_decision = await ctx.run_typed(
        "Pick specialist",
        llm_call,  # Use your preferred AI SDK here
        RunOptions(max_attempts=3),
        messages=question.message,
        tools=[tool(name=name, description=desc) for name, desc in SPECIALISTS.items()],
    )

    # 2. No specialist needed? Give a general answer
    if not routing_decision.tool_calls:
        return routing_decision.content

    # 3. Get the specialist's name
    specialist = routing_decision.tool_calls[0].function.name
    if not specialist:
        return "Unable to determine specialist"

    # 4. Call the specialist over HTTP
    response = await ctx.generic_call(
        specialist,
        "run",
        arg=question.model_dump_json().encode(),
    )
    return response.decode("utf-8")
# <end_here>

if __name__ == "__main__":
    import asyncio
    import hypercorn

    app = restate.app(
        services=[
            remote_agent_router,
            billing_agent_svc,
            account_agent_svc,
            product_agent_svc,
        ]
    )

    conf = hypercorn.Config()
    conf.bind = ["0.0.0.0:9080"]
    asyncio.run(hypercorn.asyncio.serve(app, conf))
