import restate

from account import (
    get_customer_loans,
    get_balance,
    get_transaction_history,
)
from utils.pydantic_models import ChatMessage, ChatHistory
from utils.utils import time_now
from utils.agent_session import (
    run as agent_session_run,
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
        restate_tool(get_balance),
        restate_tool(get_transaction_history),
    ],
)

loan_request_manager_agent = Agent(
    name="Loan Request Manager Agent",
    handoff_description="A helpful agent that can helps you with submitting a request for a loan and retrieving its status, and the decision made (approval and reason).",
    instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
    You are an agent that helps with:
     - giving information on the status of the loan requests
     - giving information on the decision made (approval and reason) of the loan requests
     - giving information on the status of the loan payments (monthly amount, months left)
    You are not able to help with anything else.
    If you are speaking to a customer, you probably were transferred to from the intake agent.
    You have the tools to either create new loan requests and retrieve the loan status and decision.
    Use the following routine to support the customer.
    # Routine #1
    If the customer wants to get the status of his ongoing loan payments, loan requests, and loan decisions:
    1. Make sure you know the customer ID.
    2. Use the get_customer_loans tool to retrieve the status of the loans of the customer.
    3. Retrieve the right information from the response and return it to the customer.
     
    3. If the customer asks a question that is not related to these routines, transfer back to the intake agent.
    """,
    tools=[
        restate_tool(get_customer_loans),
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
    """
    Send a message from the customer to the ChatService.
    This will be used as input to start an agent session.

    Args:
        req (ChatMessage): The message to send to the ChatService.

    Returns:
        ChatMessage: The response from the ChatService.
    """
    history = await ctx.get(CHAT_HISTORY, type_hint=ChatHistory) or ChatHistory()
    history.entries.append(req)
    ctx.set(CHAT_HISTORY, history)

    result = await ctx.object_call(
        agent_session_run,
        key=ctx.key(),  # use the customer ID as the key
        arg=AgentInput(
            starting_agent=intake_agent,
            agents=chat_agents,
            message=f"For customer ID {ctx.key()}: {req.content}",  # this is the input for the LLM call
        ),
    )

    new_message = ChatMessage(
        role="system", content=result.final_output, timestamp_millis=await time_now(ctx)
    )
    history.entries.append(new_message)
    ctx.set(CHAT_HISTORY, history)
    return new_message


@chat_service.handler(kind="shared")
async def get_chat_history(ctx: restate.ObjectSharedContext) -> ChatHistory:
    return await ctx.get(CHAT_HISTORY, type_hint=ChatHistory) or ChatHistory()
