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
    query_user_db,
    SupportTicket,
    tool,
    tool_result,
    create_support_ticket,
)


class Question(BaseModel):
    user_id: str = "user_12345"
    message: str = "On which plan am I?"


# <start_here>
tool_router = restate.Service("ToolRouter")

# Define tools as required by your LLM SDK
TOOLS = [
    tool("query_user_database", "Get user account and billing info"),
    tool(
        "create_support_ticket",
        "Create support tickets",
        SupportTicket.model_json_schema(),
    ),
]


@tool_router.handler()
async def route(ctx: restate.Context, question: Question) -> str | None:
    """Route to appropriate tool and execute until final answer"""
    messages = [{"role": "user", "content": question.message}]

    while True:
        result = await ctx.run_typed(
            "LLM call",
            llm_call,  # Use your preferred LLM SDK here
            RunOptions(max_attempts=3, type_hint=Message),
            messages=messages,
            tools=TOOLS,
        )
        messages.append(result.dict())

        if not result.tool_calls:
            return result.content

        for tool_call in result.tool_calls:
            fn = tool_call.function
            tool_name = fn.name or "unknown"
            match tool_name:
                case "query_user_database":
                    # Example of a local tool
                    result = await ctx.run_typed(
                        "Query DB", query_user_db, user_id=question.user_id
                    )
                case "create_support_ticket":
                    # Example of a remote tool/workflow
                    ticket = SupportTicket.model_validate_json(fn.arguments)
                    result = await ctx.service_call(create_support_ticket, arg=ticket)
                case _:
                    result = f"Tool not found: {tool_name}"

            messages.append(tool_result(tool_call.id, tool_name, result))


# <end_here>
