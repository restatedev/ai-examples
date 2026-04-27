# Resilient agents with Restate + LangChain
[<img src="https://raw.githubusercontent.com/restatedev/img/refs/heads/main/show-code.svg">](agent.py)

Use [LangChain's `create_agent`](https://docs.langchain.com/oss/python/langchain/agents) to build your agent, and let Restate handle the persistence and resiliency of the agent's decisions and tool executions.

The example is an agent that can search for the weather in certain city.

## Running the example

1. Export your OpenAI or Anthropic API key as an environment variable:
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
    curl localhost:8080/agent/run --json '{"message": "What is the weather in San Francisco?"}'
    ```

    Returns: `The weather in San Francisco is currently 23°C and sunny.`

Check the Restate UI (`http://localhost:9080`) to see the journals of your invocations.

## Integrating Restate with LangChain

To make the agent resilient, we attach `RestateMiddleware` to `create_agent`:

- Every LLM call is journaled by `awrap_model_call` via `ctx.run_typed("call LLM", ...)`.
- Parallel tool calls are serialized via a turnstile keyed on `tool_call_id` so the journal order is deterministic across replays.

Tool side effects are NOT auto-journaled. Wrap them yourself inside the tool body with `restate_context().run_typed("name", ...)` for the steps you want to be durable. This keeps it explicit which calls are journaled and avoids nested-`ctx.run_typed` traps.
