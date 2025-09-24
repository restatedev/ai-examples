import restate
from pydantic import BaseModel

from util import (
    llm_call,
    fetch_service_status,
    create_support_ticket,
    query_user_database,
)

"""
LLM Request Routing to Tools

Automatically route customer support requests to specialized backend tools.
Tools handle database queries, service status checks, and ticket management.

Support Request → Classifier → Database/API/CRM Tool → Operational Result
"""


# Available support tool categories
TOOLS = ["user_database", "service_status", "ticket_management"]

# Example customer support request
example_prompt = "My API calls are failing, what's wrong with my account?"
"""
Other examples:
    "What's my current subscription plan and usage limits?",
    "Is there an outage affecting the payment service?",
    "I need to report a bug with the dashboard, please create a ticket"
"""


class Prompt(BaseModel):
    user_id: str = "user_12345"
    message: str = example_prompt


# ROUTING SERVICE

tool_router_service = restate.Service("ToolRouterService")


@tool_router_service.handler()
async def route(ctx: restate.Context, prompt: Prompt) -> str:
    """Classify request and route to appropriate tool function."""

    # Classify the customer support request
    route_key = await ctx.run_typed(
        "classify_request",
        llm_call,
        prompt=f"""Classify this customer support request into one category: {list(TOOLS)}

        user_database: account info, subscription details, usage limits, billing questions, user profile
        service_status: outages, downtime, service availability, system status, performance issues
        ticket_management: bug reports, feature requests, technical issues that need escalation

        Reply with only the category name.

        Request: {prompt.message}""",
    )

    tool_category = route_key.strip().lower()

    # Route to appropriate support tool
    if tool_category == "user_database":
        tool_result = await user_database_tool(ctx, user_id=prompt.user_id)
    elif tool_category == "service_status":
        tool_result = await service_status_tool(ctx)
    elif tool_category == "ticket_management":
        tool_result = await ticket_management_tool(ctx, prompt)
    else:
        tool_result = f"Didn't find info for {tool_category}"


    response = await ctx.run_typed(
        "analyze tool output",
        llm_call,
        prompt=f"Provide a concise, friendly response to the user question {prompt} based on this info: {tool_result}",
    )

    return response


# CUSTOMER SUPPORT TOOL FUNCTIONS


async def user_database_tool(ctx: restate.Context, user_id: str) -> str:
    """Tool for querying user database - subscriptions, usage, billing info."""
    return await ctx.run_typed("query_user_db", query_user_database, user_id=user_id)


async def service_status_tool(ctx: restate.Context) -> dict[str, str]:
    """Tool for checking service status and outages via internal APIs."""
    return await ctx.run_typed("check_service_status", fetch_service_status)


async def ticket_management_tool(ctx: restate.Context, request: Prompt) -> str:
    """Tool for creating tickets in CRM system for bugs, feature requests, escalations."""
    await ctx.run_typed(
        "create support ticket",
        create_support_ticket,
        request=request.message,
        user_id=request.user_id,
    )
