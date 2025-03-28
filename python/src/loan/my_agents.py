from chat_session import receive_message
from utils.credit_worthiness_tools import calculate_credit_worthiness

from loan_approval_workflow import on_ai_assessment, get_status
from loan_approval_workflow import run as loan_approval_workflow_run
from utils.agent_session import (
    Agent,
    RECOMMENDED_PROMPT_PREFIX,
    restate_tool,
)

notification_agent = Agent(
    name="Notification Agent",
    handoff_description="A helpful agent that can helps you with sending notifications to customers and bank employees via chat messages.",
    instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
    You are an agent that helps with sending notifications to customers and bank employees via chat messages.  
    You help with converting the input into a nice, formal, kind chat message and 
    use the chat session receive_message tool to send it to the chat session.
    The key of the chat session virtual object is the chat session id.  
    Use the following routine.
    # Routine
    1. Make sure you know the chat session ID.
    2. Based on the input, generate a kind, formal chat message, personalized for the customer. 
    3. Invoke the chat tool receive_message to make the user receive a message through it's chat history.
    """,
    # TODO allow calling a handler which throws a specific error if there is no chat session ID known
    tools=[
        restate_tool(tool_call=receive_message),
    ],
)


loan_assessment_agent = Agent(
    name="Loan Review Agent",
    handoff_description="A helpful agent that can helps you with scheduling to receive an invoice after a specific delay.",
    instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
    You are an agent that helps with determining the creditworthiness of the customer.
    You decide on whether or not he should get a loan.  
    You were probably invoked by the loan approval workflow. 
    Use the following routine to support the customer.
    # Routine
    1. The input the loan approval workflow gave you contains the credit score, and transaction history of the customer. 
    The first thing you should do is analyze the transaction history of the customer.
    You do this by categorizing each of the transactions into: income, loan_payment, gambling, payday_loan, cash_withdrawal, basic_expense, other.    
    2. Then you invoke each of the tools one after the other to calculate the important metrics to base your decision on: 
    - average_monthly_spending
    - debt_to_income_ratio
    - high_risk_transactions
    - large_purchases
    3. Based on the values you get back you then make a decision to either approve or not. You can use your own judgement for this. 
    4. Invoke the on_ai_assessment tool to then let the workflow know of your decision. 
    Your decision contains a boolean on whether you approve on not, and your reasoning, together with the output of each of the tool call you did to calculate the metrics. 
    Be very clear in the reason you give so the customer can understand the decision you made.
    In case of any doubt, reject the loan application, and give as reason "NOT ENOUGH INFORMATION" together with the output of each of the tools.
    """,
    tools=[
        restate_tool(tool_call=on_ai_assessment),
        restate_tool(tool_call=calculate_credit_worthiness),
    ],
)


loan_request_manager = Agent(
    name="Loan Request Manager Agent",
    handoff_description="A helpful agent that can helps you with submitting a request for a loan and retrieving its status.",
    instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
    You are an agent that helps with submitting loan requests and retrieving the current status of a loan request.
    If you are speaking to a customer, you probably were transferred to from the intake agent.
    You have the tools to either create new loan requests and retrieve the loan status.
    Use the following routine to support the customer.
    # Routine
    If the customer wants to submit a new loan request:
    1. Make sure you know the customer ID and all the loan request information you need to submit the request. 
    You can find all the required information in the input parameters of the loan_approval_workflow run tool: loan amount, and duration.
    Don't ask for other info.
    2. Once you have all the loan request information, start a new workflow with the run tool. Use the customer ID as the workflow key.
    Always put the delay to 0 when invoking the approval workflow
    3. If the customer asks a question that is not related to the routine, transfer back to the triage agent.
    
    Alternatively, if the customer wants to get the status of his ongoing loan request:
    1. Make sure you know the customer ID.
    2. Use the get_status tool to retrieve the status of the loan approval process. The key of the loan workflow is the customer ID. 
    3. If the customer asks a question that is not related to the routine, transfer back to the triage agent.
    """,
    tools=[
        restate_tool(tool_call=loan_approval_workflow_run),
        restate_tool(tool_call=get_status),
    ],
)


intake_agent = Agent(
    name="Intake Agent",
    handoff_description="An intake agent that can delegates a customer's request to the appropriate agent.",
    instructions=(
        f"{RECOMMENDED_PROMPT_PREFIX}"
        "You are a helpful intake agent. You can use your tools to delegate questions to other appropriate agents."
    ),
    handoffs=[loan_request_manager.name],
)

agents = [intake_agent, loan_request_manager, loan_assessment_agent, notification_agent]
