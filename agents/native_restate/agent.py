import restate

from account import (
    get_balance,
    get_transaction_history, get_customer_loans,
)
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

loan_request_info_agent = Agent(
    name="Loan Request Info Agent",
    handoff_description="A helpful agent that can helps you with retrieving the status of a loan, and the decision made (approval and reason).",
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
    handoffs=[loan_request_info_agent.name, account_manager_agent.name],
)

loan_request_info_agent.handoffs.append(intake_agent.name)
account_manager_agent.handoffs.append(intake_agent.name)

chat_agents = [account_manager_agent, loan_request_info_agent, intake_agent]

# AGENT

# Keyed by conversation id
agent = restate.VirtualObject("Agent")

@agent.handler()
async def run(ctx: restate.ObjectContext, req: str) -> str:
    """
    Send a message to the agent.

    Args:
        req (str): The message to send to the agent.

    Returns:
        str: The response from the agent.
    """
    result = await agent_session_run(ctx, AgentInput(
            starting_agent=intake_agent,
            agents=chat_agents,
            message=f"For customer ID {ctx.key()}: {req}",  # this is the input for the LLM call
        ),
    )

    return result.final_output