import restate

from .util.litellm_call import llm_call
from pydantic import BaseModel

"""
Multi-Agent Routing

Automatically route requests to specialized agents based on content analysis.
Routing decisions are persisted and can be retried if they fail.

Request → Classifier → Agent A/B/C → Specialized Response
"""

# Example input text to analyze
example_prompt = "I can't log into my account. Keep getting invalid password errors."
"""
Other examples:
    "Why was I charged $49.99 when I'm on the $29.99 plan?",
    "How do I export my project data to Excel format?",
    "What's the best way to organize my dashboard widgets?"
"""


class Prompt(BaseModel):
    message: str = example_prompt


# ROUTING SERVICE

agent_router_service = restate.Service("AgentRouterService")


billing_agent = {
    "type": "function",
    "function": {
        "name": "billing_support",
        "description": "Handle billing related queries: payments, charges, refunds, plans",
    },
}

account_agent = {
    "type": "function",
    "function": {
        "name": "account_support",
        "description": "Handle account related queries: login, password, security, access",
    },
}

product_agent = {
    "type": "function",
    "function": {
        "name": "product_support",
        "description": "Handle product related queries: features, usage, best practices",
    },
}


@agent_router_service.handler()
async def route(ctx: restate.Context, prompt: Prompt) -> str:
    """Classify request and route to appropriate specialized agent."""

    # Classify the request
    result = await ctx.run_typed(
        "handle request",
        llm_call,
        restate.RunOptions(max_attempts=3),
        prompt=prompt.message,
        tools=[billing_agent, account_agent, product_agent],
    )

    if not result.tool_calls:
        return result.content

    tool_call = result.tool_calls[0]
    fn = tool_call.function
    # Route to appropriate support tool
    if fn.name == "billing_support":
        result =await ctx.run_typed(
            "run billing agent",
            llm_call,
            restate.RunOptions(max_attempts=3),
            system="You are a billing support specialist."
            "Acknowledge the billing issue, explain charges clearly, provide next steps with timeline."
            "Keep responses professional but friendly.",
            prompt=prompt.message,
        )
        return result.content
    elif fn.name == "account_support":
        result = await ctx.run_typed(
            "run account agent",
            llm_call,
            restate.RunOptions(max_attempts=3),
            system="You are an account security specialist."
            "Prioritize account security and verification, provide clear recovery steps, include security tips."
            "Maintain a serious, security-focused tone.",
            prompt=prompt.message,
        )
        return result.content
    elif fn.name == "product_support":
        result= await ctx.run_typed(
            "run product agent",
            llm_call,
            restate.RunOptions(max_attempts=3),
            system="You are a product specialist."
            "Focus on feature education and best practices, include specific examples, suggest related features."
            "Be educational and encouraging in tone.",
            prompt=prompt.message,
        )
        return result.content
    else:
        return "Sorry, I couldn't answer your request."
