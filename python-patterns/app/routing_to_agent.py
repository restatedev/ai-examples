"""
Agent Routing

Route customer questions to specialized AI agents based on their content.
Each routing decision is durable and can be retried if it fails.

Flow: Customer Question → Classifier → Specialized Agent → Response
"""

import restate

from restate import RunOptions
from pydantic import BaseModel

from .util.litellm_call import llm_call
from .util.util import tool


# Customer's question
class Question(BaseModel):
    message: str = "I can't log into my account. Keep getting invalid password errors."


# Create the routing service
router = restate.Service("AgentRouter")

# Our team of AI specialists
SPECIALISTS = {
    "BillingAgent": "Expert in payments, charges, and refunds",
    "AccountAgent": "Expert in login issues and security",
    "ProductAgent": "Expert in features and how-to guides",
}


@router.handler()
async def answer(ctx: restate.Context, question: Question) -> str:
    """Classify request and route to appropriate specialized agent."""

    # 1. First, decide if a specialist is needed
    routing_decision = await ctx.run_typed(
        "Pick specialist",
        llm_call,  # Use your preferred LLM SDK here
        RunOptions(max_attempts=3),
        system="You are a customer service routing system. Choose the appropriate specialist, or respond directly if no specialist is needed.",
        prompt=question.message,
        tools=[tool(name=name, description=desc) for name, desc in SPECIALISTS.items()],
    )

    # 2. No specialist needed? Give a general answer
    if not routing_decision.tool_calls:
        return routing_decision.content

    # 3. Get the specialist's name
    specialist = routing_decision.tool_calls[0].function.name

    # 4. Ask the specialist to answer
    answer = await ctx.run_typed(
        f"Ask {specialist}",
        llm_call,
        RunOptions(max_attempts=3),
        system=f"You are a {SPECIALISTS.get(specialist, 'support')} specialist.",
        prompt=question.message,
    )

    return answer.content
