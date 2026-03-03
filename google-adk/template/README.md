# Resilient agents with Restate + Google ADK
[<img src="https://raw.githubusercontent.com/restatedev/img/refs/heads/main/show-code.svg">](agent.py)

Use the Google ADK to implement your agent, and let Restate handle the persistence and resiliency of the agent's decisions and tool executions.

The example is an agent that can search for the weather in certain city.

<img src="https://raw.githubusercontent.com/restatedev/ai-examples/refs/heads/main/doc/img/get-started-openai/invocation_ui.png" alt="Using Agent SDK - journal" width="1200px"/>

> Also check out the Tour of Agents with [the Google ADK + Restate](../tour-of-agents)

## Running the example

1. Export your OpenAI or Anthrophic API key as an environment variable:
    ```shell
    export OPENAI_API_KEY=your_openai_api_key
    ```
2. [Start the Restate Server](https://docs.restate.dev/installation) in a separate shell:
    ```shell
    restate-server
    ```
3. Start the services:
    ```shell
    uv run .
    ```
4. Register the services:
    ```shell
    restate -y deployments register localhost:9080
    ```

5. Send requests to your agent:

    ```shell
    curl localhost:8080/agent/run --json '"What is the weather in San Francisco?"'
    ```

   Returns: `The weather in San Francisco is currently 23°C and sunny.`


Check the Restate UI (`http://localhost:9080`) to see the journals of your invocations (remove the filters).

<img src="https://raw.githubusercontent.com/restatedev/ai-examples/refs/heads/main/doc/img/get-started-openai/detailed_invocation_ui.png" alt="Using Agent SDK - journal" width="1200px"/>

## Integrating Restate with the Google ADK

To make the agent resilient, we need to:
1. **Restate Plugin**: Add `RestatePlugin()` to your Google ADK App. This enables durability for model calls and tool executions.
2. **Resilient tool execution**: Wrap tool logic in durable steps using `restate_context().run_typed()`. The result is persisted and retried until it succeeds.

## Limitations
Restate will prevent tools from executing in parallel, to avoid non-deterministic behavior on retries/resume.
We are working on a solution to this.