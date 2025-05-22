
## Mixing static, code-defined workflows with agentic workflows

**Note:** We didn't need to change anything in the agent loop to make this work.

The agent session we implemented in the previous section is just a Restate Virtual Object. 
It can be called from anywhere, also from a more traditional code-defined workflow. 
For example, imagine a [credit approval workflow](insurance_workflows/credit_review_workflow.py) where a step in the workflow is to wait on an [agent to analyze the credit application](insurance_workflows/credit_review_agent.py) and interact with the customer to request additional information if necessary.

The credit workflow is kicked off by an agentic chat session. 
It lets you interact with a [credit workflow agent](insurance_workflows) that can apply for credits, check the status of credits, and provide information about bank accounts.

The credit workflow then again starts an agent session to review the credit application and interact with the customer to request additional information if necessary.

The application looks as follows:

<img src="img/credit_approval_agents.png" alt="credit workflow app overview" width="650px"/>

You need to export your OPENAI API key as an environment variable:

```shell
export OPENAI_API_KEY=your_openai_api_key
```

To run the credit approval app::

```shell
uv run app
```

To run Restate:
```shell
restate-server
```
Register your deployment in the UI: `http://localhost:9080`



Open a new chat session and request a credit, the status of an ongoing credits or information about your bank account from the UI. 

For example:
```
Hi, I would like to apply for a credit of 1000 euros. 
```

Or:
```
Hi, what is the status of my credit?
```

When you apply for a loan the agent will kick off the loan workflow.
And you will get async updates about whether your loan has been approved or not.

<img src="img/chat_example.png" alt="Chat example"/>

Here is an example of a journal of a loan application which required extra info:

<img src="img/mixing_agents_and_workflows_journal.png" alt="Loan journal"/>

