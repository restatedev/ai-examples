# Restate-native agent implementation

This is an example of how far you can go with customizing your agentic workflows with Restate.

This example implements the agent loop directly with Restate, providing maximum control over the agent's behavior and workflow execution.

It provides full customization possibilities. For example, you can extend it to support things like interruptible agents and [saga patterns](https://docs.restate.dev/guides/sagas). and supports parallel tool calls, but requires managing and writing the agent loop yourself.

**The agent composes the workflow on the fly, and Restate persists the execution as it takes place.**

Restate powers your agents with the following features:
- 🛡️ **Automatic retries**: Built-in retry mechanisms for failed operations
- 🔐 **Recovery of decisions and tool results**: Restate retries only the failed step and preserves the rest of the progress
- 🔄 **Stateful agent sessions**: Isolate different sessions/conversations with Virtual Objects. Get isolated memory and concurrency guarantees per object. Memory is queryable from the outside and viewable in the Restate UI
- 🚀 **Scalability**: Parallel sessions with consistent state
- 🔍 **Observability**: Via the Restate UI and OTEL traces, you get line-by-line execution tracking and insight into tool executions and hand-off chains
- ⏱️ **Long-running Agentic Workflows**: Durability for any workflow from millis to months. And built-in durable timers & scheduling
- 🙂 **Resilient human-in-the-loop**: Both approaches support human intervention in workflows
- 👬 **Idempotency/deduplication**: Prevents duplicate agent requests

If we implement the agent loop with Restate, Restate journals each of the decisions the agents make and manages the tool executions.
The agent session is a Restate Virtual Object that has a handler that runs the agent loop.

<img src="https://raw.githubusercontent.com/restatedev/ai-examples/refs/heads/main/doc/img/restate-native-agent/agentic_workflow.png" alt="Agentic workflow" width="650px"/>

## Running the example

This example implements a bank agent that can answer questions about your balance, loans and transactions.

1. Export your OpenAI or Anthrophic API key as an environment variable:
    ```shell
    export OPENAI_API_KEY=your_openai_api_key
    ```
2. [Start the Restate Server](https://docs.restate.dev/develop/local_dev) in a separate shell:
    ```shell
    restate-server
    ```
3. Start the service:
    ```shell
    uv run .
    ```
4. Register the services: 
    ```shell
    restate -y deployments register localhost:9080 --force
    ```
   
Now you can send requests to the agent via the UI playground (click on the agent service and then `playground`):

<img src="https://raw.githubusercontent.com/restatedev/ai-examples/refs/heads/main/doc/img/restate-native-agent/ui_example.png" alt="UI example" width="1200px"/>

Or with the [client](client.py):

- **Request**: 
   ```shell
   uv run client.py "how much is my balance?"
   ```
   Example response: `Your current balance is $100,000.00. If you have any other questions, feel free to ask!`

    <img src="https://raw.githubusercontent.com/restatedev/ai-examples/refs/heads/main/doc/img/restate-native-agent/journal.png" alt="UI example" width="1200px"/>

- **Request**:
   ```shell
   uv run client.py "how much did I spend on gambling last month?"
   ```
   Example response: `I reviewed your transactions from last month, and it appears you didn't spend any money on gambling during that period. If you have any other questions or need further clarification, please let me know!`

- **Request**: 
   
   ```shell
   uv run client.py "give me an overview of my outstanding loans and credit"
   ```
   
   Example response:
   ```
   Here's an overview of your outstanding loans:
   
   1. **Car Purchase Loan**
      - **Amount**: $10,000
      - **Duration**: 12 months
      - **Approved**: Yes
      - **Reason**: Good credit score and no risky transactions like gambling.
      - **Monthly Payment**: $9,856.07
      - **Months Left**: 11
   
   If you need more information, feel free to ask!
   ```
   
You can see the state of your agent in the state tab in the UI:

<img src="https://raw.githubusercontent.com/restatedev/ai-examples/refs/heads/main/doc/img/restate-native-agent/state_agent.png" alt="UI state" width="600px"/>