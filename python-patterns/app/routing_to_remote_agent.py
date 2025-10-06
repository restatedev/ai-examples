import restate
import json
from .util.litellm_call import llm_call
from pydantic import BaseModel

"""
Multi-Agent Routing

Automatically route requests to specialized agents based on content analysis.
Routing decisions are persisted and can be retried if they fail.
Agents can be deployed as separate services, to scale independently.

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


# ROUTING AGENT

remote_agent_router_service = restate.Service("RemoteAgentRouterService")


@remote_agent_router_service.handler()
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

    # We use a generic call to route to the specialized agent service
    # Generic calls let us call agents by string name and method
    response = await ctx.generic_call(
        tool_call.function.name,
        "run",
        arg=json.dumps(prompt.message).encode("utf-8"),
    )
    return response.decode("utf-8")


# SPECIALIZED AGENT SERVICES

# Billing Support Agent
billing_agent = {
    "type": "function",
    "function": {
        "name": "BillingAgent",
        "description": "Handle billing related queries: payments, charges, refunds, plans",
    },
}


billing_agent_svc = restate.Service("BillingAgent")


@billing_agent_svc.handler("run")
async def get_billing_support(ctx: restate.Context, prompt: str) -> str:
    result = await ctx.run_typed(
        "billing_response",
        llm_call,
        restate.RunOptions(max_attempts=3),
        system=f"""You are a billing support specialist.
        Acknowledge the billing issue, explain charges clearly, provide next steps with timeline.
        Keep responses professional but friendly.""",
        prompt=prompt,
    )
    return result.content


# Account Security Agent
account_agent = {
    "type": "function",
    "function": {
        "name": "AccountAgent",
        "description": "Handle account related queries: login, password, security, access",
    },
}

account_agent_svc = restate.Service("AccountAgent")


@account_agent_svc.handler("run")
async def get_account_support(ctx: restate.Context, prompt: str) -> str:
    result = await ctx.run_typed(
        "account_response",
        llm_call,
        restate.RunOptions(max_attempts=3),
        system=f"""You are an account security specialist.
        Prioritize account security and verification, provide clear recovery steps, include security tips.
        Maintain a serious, security-focused tone.""",
        prompt=prompt,
    )
    return result.content


# Product Support Agent
product_agent = {
    "type": "function",
    "function": {
        "name": "ProductAgent",
        "description": "Handle product related queries: features, usage, best practices",
    },
}

product_agent_svc = restate.Service("ProductAgent")


@product_agent_svc.handler("run")
async def get_product_support(ctx: restate.Context, prompt: str) -> str:
    result = await ctx.run_typed(
        "product_response",
        llm_call,
        restate.RunOptions(max_attempts=3),
        system=f"""You are a product specialist.
        Focus on feature education and best practices, include specific examples, suggest related features.
        Be educational and encouraging in tone.""",
        prompt=prompt,
    )
    return result.content
