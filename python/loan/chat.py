import json
import restate

from account import (
    get_customer_loans,
    submit_loan_request,
    get_balance,
    get_transaction_history,
)
from utils.pydantic_models import ChatMessage, ChatHistory
from utils.utils import time_now
from utils.agent_session import (
    run,
    AgentInput,
    restate_tool,
    Agent,
    RECOMMENDED_PROMPT_PREFIX,
)

# AGENTS

account_manager_agent = Agent(
    name="Account Manager Agent",
    handoff_description="A helpful agent that can helps you with answering questions about your bank account: the balance and transaction history.",
    instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
    You are an agent that helps with answering questions about the bank account: related to the balance and transaction history.
    You are not able to help with anything else.
    If you are speaking to a customer, you probably were transferred to from the intake agent.
    You have the tools to retrieve the transaction history and the balance.
    Use the following routine to support the customer.
    # Routine #1
    1. Make sure you know the customer ID. This will be the key for all interaction with the tools. 
    Never use another key as the customer ID you find at the top of the chat message. 
    2. Use the get_balance and get_transaction_history tools to retrieve the balance or the transaction history of the customer.
    Depending on the customer question, use the right tool.
    3. Analyze the response and return the right information to the customer in a kind, polite, formal message.
    4. If the customer asks a question that is not related to these routines, transfer back to the intake agent.
    """,
    tools=[
        restate_tool(tool_call=get_balance),
        restate_tool(tool_call=get_transaction_history),
    ],
)

loan_request_manager_agent = Agent(
    name="Loan Request Manager Agent",
    handoff_description="A helpful agent that can helps you with submitting a request for a loan and retrieving its status, and the decision made (approval and reason).",
    instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
    You are an agent that helps with:
     - submitting loan requests
     - giving information on the status of the loan requests
     - giving information on the decision made (approval and reason) of the loan requests
     - giving information on the status of the loan payments (monthly amount, months left)
    You are not able to help with anything else.
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
    Alternatively, if the customer wants to get the status of his ongoing loan payments, loan requests, and loan decisions:
    1. Make sure you know the customer ID.
    2. Use the get_customer_loans tool to retrieve the status of the loans of the customer.
    3. Retrieve the right information from the response and return it to the customer.
     
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
    handoffs=[loan_request_manager_agent.name, account_manager_agent.name],
)

loan_request_manager_agent.handoffs.append(intake_agent.name)
account_manager_agent.handoffs.append(intake_agent.name)

chat_agents = [account_manager_agent, loan_request_manager_agent, intake_agent]

# CHAT SERVICE

# Keyed by customerID
chat_service = restate.VirtualObject("ChatService")

# Keys of the K/V state stored in Restate per chat
CHAT_HISTORY = "chat_history"


@chat_service.handler()
async def send_message(ctx: restate.ObjectContext, req: ChatMessage) -> ChatMessage:
    history = await ctx.get(CHAT_HISTORY, type_hint=ChatHistory) or ChatHistory()
    history.entries.append(req)
    ctx.set(CHAT_HISTORY, history)

    result = await ctx.object_call(
        run,
        key=ctx.key(),  # use the customer ID as the key
        arg=AgentInput(
            starting_agent=intake_agent,
            agents=chat_agents,
            message=f"For customer ID {ctx.key()}: {req.content}",  # this is the input for the LLM call
        ),
    )

    print(result)

    content = json.loads(result.messages[-1]["content"])["content"][-1]["text"]
    new_message = ChatMessage(
        role="system", content=content, timestamp=await time_now(ctx)
    )
    history.entries.append(new_message)
    ctx.set(CHAT_HISTORY, history)
    return new_message


@chat_service.handler()
async def receive_message(ctx: restate.ObjectContext, req: ChatMessage):
    """
    Add a message to the chat history of this chat session.
    This can be used to let the bank send messages to the customer.

    Args:
        req (ChatMessage): The message to add to the chat history
    """
    chat_history = await ctx.get(CHAT_HISTORY, type_hint=ChatHistory) or ChatHistory()
    chat_history.entries.append(req)
    ctx.set(CHAT_HISTORY, chat_history)


@chat_service.handler(kind="shared")
async def get_chat_history(ctx: restate.ObjectSharedContext) -> ChatHistory:
    return await ctx.get(CHAT_HISTORY, type_hint=ChatHistory) or ChatHistory()
