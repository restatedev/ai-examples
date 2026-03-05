# Restate Agent Template - Python

A template for creating a Restate agent in TypeScript.

## Run the example
1. Export your OpenAI API key as an environment variable:
    ```shell
    export OPENAI_API_KEY=your_openai_api_key
    ```
2. [Start the Restate Server](https://docs.restate.dev/installation) in a separate shell:
    ```shell
    restate-server
    ```
3. Start the agent:
    ```shell
    uv run .
    ```
4. Register the services (use `--force` if you already had another deployment registered at 9080):
    ```shell
    restate -y deployments register localhost:9080 --force
    ```
5. Send a message to the agent:
    ```shell
    curl localhost:8080/agent/run --json '{"message":"What is the weather in San Francisco?"}'
   ```