"""
Agent Routing

Route customer questions to specialized AI agents based on their content.
Each routing decision is durable and can be retried if it fails.

Flow: Customer Question → Classifier → Specialized Agent → Response
"""

import restate

from pydantic import BaseModel
from restate import RunOptions

from .util.util import tool
from .util.litellm_call import llm_call


# Customer's question
class Question(BaseModel):
    message: str = "I can't log into my account. Keep getting invalid password errors."


remote_agent_router = restate.Service("RemoteAgentRouter")

# Classify the request
SPECIALISTS = {
    "BillingAgent": "Expert in payments, charges, and refunds",
    "AccountAgent": "Expert in login issues and security",
    "ProductAgent": "Expert in features and how-to guides",
}


@remote_agent_router.handler()
async def answer_question(ctx: restate.Context, question: Question) -> str:
    """Classify request and route to appropriate specialized agent."""

    # 1. First, decide if a specialist is needed
    routing_decision = await ctx.run_typed(
        "Pick specialist",
        llm_call,
        RunOptions(max_attempts=3),  # Retry up to 3 times if needed
        prompt=question.message,
        tools=[tool(name=name, description=desc) for name, desc in SPECIALISTS.items()],
    )

    # 2. No specialist needed? Give a general answer
    if not routing_decision.tool_calls:
        return routing_decision.content

    # 3. Get the specialist's name
    specialist = routing_decision.tool_calls[0].function.name

    # 4. Call the specialist over HTTP
    response = await ctx.generic_call(
        specialist,
        "run",
        arg=question.model_dump_json().encode(),
    )
    return response.decode("utf-8")
