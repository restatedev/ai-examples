# Resilient agents with Restate + Pydantic AI

Use [Pydantic AI](https://ai.pydantic.dev/) to implement your agent, and let Restate handle the persistence and resiliency of the agent's decisions and tool executions.

The example is an agent that can search for the weather in a certain city.

## Running the example

Check out the [AI Quickstart](https://docs.restate.dev/ai-quickstart) to run this example.

1. Export your OpenAI API key as an environment variable:
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


Check the Restate UI (`http://localhost:9070`) to see the journals of your invocations.

## Integrating Restate with Pydantic AI

The `RestateAgent` wrapper makes your Pydantic AI agent durable. Use the Restate Context in your tools to make tool steps recoverable.

On recovery, Restate replays the journaled results instead of re-executing LLM and tool calls, so your agent resumes exactly where it left off.

## Limitations
Restate will prevent tools from executing in parallel, to avoid non-deterministic behavior on retries/resume.
We are working on a solution to this.
