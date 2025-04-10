import restate

from account import (
    get_customer_loans,
    submit_loan_request,
    get_balance,
    get_transaction_history,
)
from loan_review_agent import on_additional_info
from utils.pydantic_models import ChatMessage, ChatHistory
from utils.utils import time_now
from utils.agent_session import (
    run as agent_session_run,
    AgentInput,
    restate_tool,
    Agent,
    RECOMMENDED_PROMPT_PREFIX,
)


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


@chat_service.handler()
async def add_async_response(ctx: restate.ObjectContext, req: ChatMessage) -> str:
    """
    Add a message to the chat history of this chat session.
    This can be used to let the bank send messages to the customer.

    Args:
        req (ChatMessage): The message to add to the chat history
    """
    chat_history = await ctx.get(CHAT_HISTORY, type_hint=ChatHistory) or ChatHistory()
    chat_history.entries.append(req)
    ctx.set(CHAT_HISTORY, chat_history)
    return "Message sent to customer."


@chat_service.handler(kind="shared")
async def get_chat_history(ctx: restate.ObjectSharedContext) -> ChatHistory:
    return await ctx.get(CHAT_HISTORY, type_hint=ChatHistory) or ChatHistory()


# AGENTS

account_manager_agent = Agent(
    name="Account Manager Agent",
    handoff_description="A helpful agent that helps with answering questions about your bank account balance and transaction history.",
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

loan_status_retriever = Agent(
    name="Loan Status Retriever Agent",
    handoff_description="A helpful agent that helps retrieving the status of ongoing loan requests and the decision made (approval and reason).",
    instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
    You are an agent that retrieves the status of ongoing loan requests and the decision made.
    You are not able to help with anything else.
    If you are speaking to a customer, you probably were transferred to from the intake agent.
    Use the following routine to support the customer.
    Don't give any reponse to the customer until you finished the entire routine.
    # Routine
    1. Make sure you know the customer ID.
    2. Use the get_customer_loans tool to retrieve the status of the loans of the customer.
    3. Retrieve the right information from the response and return it to the customer.
    4. If the customer asks a question that is not related to this routine, transfer back to the intake agent.
    """,
    tools=[
        restate_tool(get_customer_loans),
    ],
)

loan_request_submitter = Agent(
    name="Loan Request Submitter Agent",
    handoff_description="A helpful agent that helps with submitting a request for a loan",
    instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
    You are a helpful agent that can submit loan requests. You were probably transferred from the intake agent.
    Use the following routine to support the customer. Don't say, ask or respond anything that is not part of the routine. Follow it strictly.
    **Never say you submitted a loan request unless you finished the entire routine and executed the submit_loan_request tool!!!**
    # Routine
    1. Make sure you know the customer ID and all the loan request information you need to submit the request. 
    Don't ask for other info besides that.
    2. Once you have all the loan request information, submit the workflow with the submit_loan_request tool, and use the customer ID as the key.
    3. Let the customer know the loan got submitted and include the loan ID. You can find the loan ID as the response of the submit_loan_request tool.
    4. If the customer asks a question that is not related to this routine, transfer back to the intake agent.
    """,
    tools=[
        restate_tool(submit_loan_request),
    ]
)

clarifications_forwarder_agent = Agent(
    name="Clarifications Answer Forwarder Agent",
    handoff_description="""
    A helpful agent that helps with forwarding the customer's clarifications of suspicious transactions (gambling, debt, high-risk purchases etc) to ongoing loan approval processes.
    """,
    instructions=f"""{RECOMMENDED_PROMPT_PREFIX}    
    You help forwarding clarifications the customer provides to ongoing loan approval processes.

    You are not able to help with anything else.
    Forward the clarifications to the loan approval process by following the instructions below.
    
    # Routine #1
    1. Use the on_additional_info tool to route the additional information the customer gave back to the loan approval process. Use the loan ID as the key.
    If you are not sure about the loan ID, ask the customer for it.
    2. If the customer asks a question that is not related to these routines, transfer back to the intake agent.
    """,
    tools=[
        restate_tool(on_additional_info)
    ]
)


message_to_customer_agent = Agent(
    name="Message to Customer Agent",
    handoff_description="A helpful agent that can forwards messages from the system to the customer.",
    instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
    You are an agent that helps with forwarding messages from the system to the customer.
    Use the following routine to support the customer.
    If the message is not a REQUEST for clarifications (e.g. the answer to it), then handoff to the intake agent, otherwise use the routine and the add_async_response.
    Routine #1
    1. Make sure you know the customer ID. 
    2. Use the add_async_response tool with the Customer ID as key. The role of the message is "system". 
    """,
    tools=[
        restate_tool(add_async_response),
    ],
)

intake_agent = Agent(
    name="Intake Agent",
    handoff_description="An intake agent that delegates a customer's request to the appropriate agent.",
    instructions=(
        f"{RECOMMENDED_PROMPT_PREFIX}"
        "You are a helpful intake agent. You use handoffs to delegate questions to other appropriate agents."
        "Don't draw attention to handoffs in your conversation with the customer."
        "If the question is not related to loans, or bank accounts, then tell the customer you can't help him."
        "Otherwise transfer to another agent, and don't answer directly!"
    ),
    handoffs=[loan_request_submitter.name, loan_status_retriever.name, account_manager_agent.name, clarifications_forwarder_agent.name],
)


loan_request_submitter.handoffs.append(intake_agent.name)
loan_status_retriever.handoffs.append(intake_agent.name)
account_manager_agent.handoffs.append(intake_agent.name)
clarifications_forwarder_agent.handoffs.append(intake_agent.name)
message_to_customer_agent.handoffs.append(intake_agent.name)

chat_agents = [
    account_manager_agent,
    loan_request_submitter,
    loan_status_retriever,
    clarifications_forwarder_agent,
    message_to_customer_agent,
    intake_agent,
]

