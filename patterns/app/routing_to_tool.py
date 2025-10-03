import restate
from litellm.types.utils import Message
from pydantic import BaseModel
from restate import RunOptions

from .util.litellm_call import llm_call
from .util.util import (
    create_support_ticket,
    fetch_service_status,
    query_user_db,
    SupportTicket,
)

"""
LLM Request Routing to Tools

Automatically route customer support requests to specialized backend tools.
Tools handle database queries, service status checks, and ticket management.

Support Request → Classifier → Database/API/CRM Tool → Operational Result
"""


# TOOLS
service_status_tool = {
    "type": "function",
    "function": {
        "name": "fetch_service_status",
        "description": "Tool for checking service status and outages via internal APIs. "
        "Call this to get current status of services, incidents, and uptime.",
    },
}

create_ticket_tool = {
    "type": "function",
    "function": {
        "name": "create_support_ticket",
        "description": "Tool for creating tickets in CRM system for bugs, feature requests, escalations. "
        "Call this to log new issues reported by users.",
        "parameters": SupportTicket.model_json_schema(),
    },
}

user_database_tool = {
    "type": "function",
    "function": {
        "name": "query_user_database",
        "description": "Get human review for content that may violate policy. "
        "Call this for queries about account info, subscription details, "
        "usage limits, billing questions, user profile",
    },
}

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
    messages = [{"role": "user", "content": prompt.message}]

    # Classify the customer support request
    result = await ctx.run_typed(
        "LLM call",
        llm_call,
        RunOptions(max_attempts=3, type_hint=Message),
        messages=messages,
        tools=[create_ticket_tool, service_status_tool, user_database_tool],
    )
    messages.append(result)

    if not result.tool_calls:
        return result.content

    for tool_call in result.tool_calls:
        fn = tool_call.function
        # Route to appropriate support tool
        if fn.name == "query_user_database":
            tool_result = await ctx.run_typed(
                "Query user DB", query_user_db, user_id=prompt.user_id
            )
        elif fn.name == "fetch_service_status":
            tool_result = await ctx.run_typed(
                "Get service status", fetch_service_status
            )
        elif fn.name == "create_ticket":
            tool_result = await ctx.run_typed(
                "create support ticket",
                create_support_ticket,
                ticket=SupportTicket.model_validate_json(fn.arguments),
            )
        else:
            tool_result = f"Didn't find tool for {fn.name}"
        messages.append(
            {
                "tool_call_id": tool_call.id,
                "role": "tool",
                "name": fn.name,
                "content": tool_result,
            }
        )

    # Final response to user based on tool result
    return await ctx.run_typed(
        "analyze tool output",
        llm_call,
        RunOptions(max_attempts=3, type_hint=Message),
        prompt=f"Provide a concise, friendly response to the user question {prompt.message} based on the tool output.",
        messages=messages,
    )
