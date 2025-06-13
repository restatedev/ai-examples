# Resilient agents with Restate + OpenAI Agents Python SDK

**Give your agentic workflow the same resiliency and capabilities as what you get with a "traditional" workflow.**

**The agent composes the workflow on the fly, and Restate persists the execution as it takes place.**

Combining Restate and an Agent SDK is ideal for turning brittle agent implementations into resilient ones. 

Restate powers your agents with the following features:
- 🛡️ **Automatic retries**: Built-in retry mechanisms for failed operations
- 🔐 **Recovery of decisions and tool results**: Restate retries only the failed step and preserves the rest of the progress
- 🔄 **Stateful agent sessions**: Isolate different sessions/conversations with Virtual Objects. Get isolated memory and concurrency guarantees per object. Memory is queryable from the outside and viewable in the Restate UI
- 🚀 **Scalability**: Parallel sessions with consistent state
- 🔍 **Observability**: Via the Restate UI and OTEL traces, you get line-by-line execution tracking and insight into tool executions and hand-off chains
- ⏱️ **Long-running Agentic Workflows**: Durability for any workflow from millis to months. And built-in durable timers & scheduling
- 🙂 **Resilient human-in-the-loop**: Both approaches support human intervention in workflows
- 👬 **Idempotency/deduplication**: Prevents duplicate agent requests

## Plugging Restate into existing Agent SDKs
Combine Restate's durability with existing Agent SDKs for rapid development.

To make the agent resilient, we need to:
- persist the results of LLM calls in Restate's journal by wrapping them in `ctx.run()`
- have the context available to us in the tools so that we can use it to persist the intermediate tool execution steps.

The details of how to do this depend on the Agent SDK you are using.

⚠ **LIMITATIONS**: You cannot do parallel tool calls or any type of parallel execution if you integrate Restate with an Agent SDK. 
If you execute actions on the context in different tools in parallel, Restate will not be able to deterministically replay them because the order might be different during recovery and will crash. 
We are working on a solution to this, but for now, you can only use Restate with Agent SDKs for sequential tool calls.

### Restate + OpenAI Agent SDK
[<img src="https://raw.githubusercontent.com/restatedev/img/refs/heads/main/show-code.svg">](openai_sdk/agent.py)

Use the OpenAI Agent SDK to implement the agent loop, while Restate handles the persistence and resiliency of the agent's decisions and tool executions.

The OpenAI Agent SDK lets you wrap the LLM calls into durable actions by implementing a Restate Model Provider ([code](openai_sdk/middleware.py)).
In order to have access to the Restate context in the tools, we can pass it along in the context that we pass to the tools. 

The example is a customer service agent for an airline that can send invoices and update seat bookings.
This is [an OpenAI SDK example](https://github.com/openai/openai-agents-python/blob/main/examples/customer_service/main.py) that has been adapted to use Restate for resiliency and workflow guarantees:

<img src="img/using_agent_sdk.png" alt="Using Agent SDK" width="650px"/>

<img src="img/invocation_ui_agent_sdk.png" alt="Using Agent SDK - journal" width="1200px"/>
<img src="img/invocation_ui_agent_state.png" alt="Using Agent SDK - state" width="1200px"/>

### Other Agent SDKs
Are you using another Agent SDK? We can help you evaluate whether it can be integrated with Restate. 
Join our [Discord](https://discord.gg/skW3AZ6uGd) or [Slack](https://join.slack.com/t/restatecommunity/shared_invite/zt-2v9gl005c-WBpr167o5XJZI1l7HWKImA) to discuss.

## Running the examples

### Restate + OpenAI Agent SDK 
[<img src="https://raw.githubusercontent.com/restatedev/img/refs/heads/main/show-code.svg">](openai_sdk/agent.py)

This example implements an airline customer service agent that can answer questions about your flights, and change your seat.

The example uses the OpenAI Agent SDK to implement the agent. Although this could be adapted to other agent SDKs.

1. Export your OpenAI or Anthrophic API key as an environment variable:
    ```shell
    export OPENAI_API_KEY=your_openai_api_key
    ```
2. [Start the Restate Server](https://docs.restate.dev/develop/local_dev) in a separate shell:
    ```shell
    restate-server
    ```
3. Start the services:
    ```shell
    cd openai_sdk
    uv run .
    ```
4. Register the services: 
    ```shell
    restate -y deployments register localhost:9080 --force
    ```

Now you can send requests to the agent via the UI playground (click on the agent service and then `playground`):

<img src="img/ui_openai.png" alt="UI example" width="1000px"/>

Or with the [client](client/__main__.py):

- **Request**: 
   
   ```shell
    uv run client "can you send me an invoice for booking AB4568?"          
   ```
   
   Example response: `I've sent the invoice to your email associated with confirmation number AB4568. If there's anything else you need, feel free to ask!.`

- **Or have longer conversations**: 
   
   ```shell
   uv run client "can you change my seat to 10b?"
   ```
   
   Example response: `To change your seat to 10B, I'll need your confirmation number. Could you please provide that?`

   Respond to the question by sending a new message to the same stateful session:
   ```shell
   uv run client "5666"                         
   ```
   
   Example response: `Your seat has been successfully changed to 5B. If there's anything else you need, feel free to ask!`

Don't forget to check the Restate UI (`http://localhost:9080`) to see the journals of your invocations (remove the filters) and the state tab.
