import restate
from agents import Agent
from restate.ext.openai import DurableRunner

from app.utils.utils import send_email

# Let users request to be alerted when long-running agent tasks complete.
# For example, when a user click on a "Notify" button in the UI, the agent 
# response is send via an email when it's ready.

agent_service = restate.Workflow("AsyncNotificationsAgent")

agent = Agent(
    name="Assistant",
    instructions="You are a helpful assistant.",
)


@agent_service.main()
async def on_send(ctx: restate.WorkflowContext, user_query: str):
    # Process the user's query with the AI agent
    response = await DurableRunner.run(agent, user_query)

    # Notify other handlers of the response
    await ctx.promise("agent_response").resolve(response.final_output)

    # Return synchronous response
    return response.final_output


@agent_service.handler()
async def on_notify(ctx: restate.WorkflowContext, email: str):
    # Wait for the agent's response
    response = await ctx.promise("agent_response", type_hint=str).value()

    # Send the email
    await ctx.run_typed("Email", send_email, email=email, body=response)
