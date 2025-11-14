"""
Tool Routing

Route requests to tools based on LLM instructions.
Agent loop continues calling tools until a final answer is returned.

Flow: User Request → LLM → Tool Selection → Tool Execution → Response
"""

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
    tool, tool_result,
)


class Question(BaseModel):
    user_id: str = "user_12345"
    message: str = "My API calls are failing, what's wrong with my account?"


tool_router = restate.Service("ToolRouter")

TOOLS = [
    tool("fetch_service_status", "Check service status and outages"),
    tool("query_user_database", "Get user account and billing info"),
    tool(
        "create_support_ticket",
        "Create support tickets",
        SupportTicket.model_json_schema(),
    ),
]


@tool_router.handler()
async def route(ctx: restate.Context, question: Question) -> str:
    """Route to appropriate tool and execute until final answer"""
    messages = [{"role": "user", "content": question.message}]

    while True:
        result = await ctx.run_typed(
            "LLM call",
            llm_call,
            RunOptions(max_attempts=3, type_hint=Message),
            messages=messages,
            tools=TOOLS,
        )
        messages.append(result.dict())

        if not result.tool_calls:
            return result.content

        for tool_call in result.tool_calls:
            fn = tool_call.function
            match fn.name:
                case "query_user_database":
                    result = await ctx.run_typed(
                        fn.name, query_user_db, user_id=question.user_id
                    )
                case "fetch_service_status":
                    result = await ctx.run_typed(fn.name, fetch_service_status)
                case "create_support_ticket":
                    ticket = SupportTicket.model_validate_json(fn.arguments)
                    result = await ctx.run_typed(
                        fn.name, create_support_ticket, ticket=ticket
                    )
                case _:
                    result = f"Tool not found: {fn.name}"

            messages.append(tool_result(tool_call.id, fn.name, result))
