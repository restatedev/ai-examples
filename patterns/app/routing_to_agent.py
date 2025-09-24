import restate
import json
from util import llm_call
from pydantic import BaseModel

"""
LLM Request Routing

Automatically route requests to specialized agents based on content analysis.
Each route is handled by a dedicated agent service with domain expertise.

Request → Classifier → Agent A/B/C → Specialized Response
"""


# Specialized agent service names
AGENTS = {"billing": "BillingAgent", "account": "AccountAgent", "product": "ProductAgent"}

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


@agent_router_service.handler()
async def route(ctx: restate.Context, prompt: Prompt) -> str:
    """Classify request and route to appropriate specialized agent."""

    # Classify the request
    route_key = await ctx.run(
        "classify_request",
        lambda: llm_call(
            f"""Classify this support request into one category: {AGENTS.keys()}

        billing: payments, charges, refunds, plans
        account: login, password, security, access
        product: features, usage, best practices

        Reply with only the category name.

        Request: {prompt.message}"""
        ),
    )

    agent_service = AGENTS.get(route_key.strip().lower()) or "ProductAgent"

    # Route to specialized agent
    response = await ctx.generic_call(
        agent_service, "run", arg=json.dumps(prompt.message).encode("utf-8")
    )

    return response.decode("utf-8")


# SPECIALIZED AGENT SERVICES

# Billing Support Agent
billing_agent = restate.Service("BillingAgent")


@billing_agent.handler()
async def run(ctx: restate.Context, prompt: str) -> str:
    return await ctx.run(
        "billing_response",
        lambda: llm_call(
            f"""You are a billing support specialist.
        Acknowledge the billing issue, explain charges clearly, provide next steps with timeline.
        Keep responses professional but friendly.

        Input: {prompt}"""
        ),
    )


# Account Security Agent
account_agent = restate.Service("AccountAgent")


@account_agent.handler()
async def run(ctx: restate.Context, prompt: str) -> str:
    return await ctx.run(
        "account_response",
        lambda: llm_call(
            f"""You are an account security specialist.
        Prioritize account security and verification, provide clear recovery steps, include security tips.
        Maintain a serious, security-focused tone.

        Input: {prompt}"""
        ),
    )


# Product Support Agent
product_agent = restate.Service("ProductAgent")


@product_agent.handler()
async def run(ctx: restate.Context, prompt: str) -> str:
    return await ctx.run(
        "product_response",
        lambda: llm_call(
            f"""You are a product specialist.
        Focus on feature education and best practices, include specific examples, suggest related features.
        Be educational and encouraging in tone.

        Input: {prompt}"""
        ),
    )
