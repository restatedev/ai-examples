import datetime
import json
from datetime import datetime

import restate
from pydantic import BaseModel
from typing import Any

from account import get_customer_loans, submit_loan_request
from utils.agent_session import (
    run,
    AgentInput,
    restate_tool,
    Agent,
    RECOMMENDED_PROMPT_PREFIX,
)

# AGENTS

loan_request_manager = Agent(
    name="Loan Request Manager Agent",
    handoff_description="A helpful agent that can helps you with submitting a request for a loan and retrieving its status, and the decision made (approval and reason).",
    instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
    You are an agent that helps with submitting loan requests and retrieving the current status and decision of a loan request.
    If you are speaking to a customer, you probably were transferred to from the intake agent.
    You have the tools to either create new loan requests and retrieve the loan status and decision.
    Use the following routine to support the customer.
    # Routine #1
    If the customer wants to submit a new loan request:
    1. Make sure you know the customer ID and all the loan request information you need to submit the request. 
    You can find all the required information in the input parameters of the loan_approval_workflow run tool: loan amount, and duration.
    Don't ask for other info besides that.
    2. Once you have all the loan request information, submit the workflow with the submit_loan_request tool, and use the customer ID as the key.

    # Routine #2
    Alternatively, if the customer wants to get the status of his ongoing loan request:
    1. Make sure you know the customer ID.
    2. Use the get_customer_loans tool to retrieve the status of the loans of the customer.
     
    3. If the customer asks a question that is not related to these routines, transfer back to the intake agent.
    """,
    tools=[
        restate_tool(tool_call=submit_loan_request),
        restate_tool(tool_call=get_customer_loans),
    ],
)

intake_agent = Agent(
    name="Intake Agent",
    handoff_description="An intake agent that can delegates a customer's request to the appropriate agent.",
    instructions=(
        f"{RECOMMENDED_PROMPT_PREFIX}"
        "You are a helpful intake agent. You can use your handoffs to delegate questions to other appropriate agents."
    ),
    handoffs=[loan_request_manager.name],
)

loan_request_manager.handoffs.append(intake_agent.name)

chat_agents = [loan_request_manager, intake_agent]

# MODELS


class ChatMessage(BaseModel):
    """
    A chat message object.

    Args:
        role (str): The role of the sender (user, assistant, system).
        content (str): The message to send.
        timestamp (int): The timestamp of the message in millis.
    """

    role: str
    content: str
    timestamp: int


class ChatHistory(BaseModel):
    """
    A chat history object.

    Args:
        entries (list[ChatMessage]): The list of chat messages.
    """

    entries: list[ChatMessage]


# CHAT SERVICE

# Keyed by customerID
chat_service = restate.VirtualObject("ChatService")


@chat_service.handler()
async def send_message(
    ctx: restate.ObjectContext, req: ChatMessage
) -> list[dict[str, Any]]:
    chat_history = await ctx.get("chat_history", type_hint=ChatHistory) or ChatHistory(
        entries=[]
    )
    chat_history.entries.append(req)
    ctx.set("chat_history", chat_history)

    result = await ctx.object_call(
        run,
        key=ctx.key(),  # use the customer ID as the key
        arg=AgentInput(
            starting_agent=intake_agent,
            agents=chat_agents,
            message=f"For customer ID {ctx.key()}: {req.content}",  # this is the input for the LLM call
        ),
    )

    chat_history = await ctx.get("chat_history", type_hint=ChatHistory) or ChatHistory(
        entries=[]
    )
    new_message = json.loads(result.messages[-1]["content"])["content"][-1]["text"]
    time_now = await ctx.run("time", lambda: round(datetime.now().timestamp() * 1000))
    chat_history.entries.append(
        ChatMessage(role="system", content=new_message, timestamp=time_now)
    )
    ctx.set("chat_history", chat_history)
    return new_message


@chat_service.handler()
async def receive_message(ctx: restate.ObjectContext, req: ChatMessage):
    """
    Add a message to the chat history of this chat session.
    This can be used to let the bank send messages to the customer.

    Args:
        req (ChatMessage): The message to add to the chat history
    """
    chat_history = await ctx.get("chat_history", type_hint=ChatHistory) or ChatHistory(
        entries=[]
    )
    chat_history.entries.append(req)
    ctx.set("chat_history", chat_history)


@chat_service.handler(kind="shared")
async def get_chat_history(ctx: restate.ObjectSharedContext) -> ChatHistory:
    return await ctx.get("chat_history", type_hint=ChatHistory) or ChatHistory(
        entries=[]
    )
