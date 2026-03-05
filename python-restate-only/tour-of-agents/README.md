# Durable Restate agents - Python
This repository contains a collection of examples that show how to use Restate to build robust, fault-tolerant AI agents.

These examples do not use an Agent SDK, but instead use the Restate Python SDK together with LiteLLM to write customizable, resilient agents. 

Check out the [Restate documentation](https://docs.restate.dev/ai) for more information on each example.

## Running the examples

1. Export your OpenAI API key as an environment variable:
    ```shell
    export OPENAI_API_KEY=your_openai_api_key
    ```
2. [Start the Restate Server](https://docs.restate.dev/installation) in a separate shell:
    ```shell
    restate-server
    ```
3. Start the agent you want to run:
    ```shell
    uv run app/chat_agent.py
    ```
4. Register the services (use `--force` if you already had another deployment registered at 9080): 
    ```shell
    restate -y deployments register localhost:9080 --force
    ```
5. In the UI, click on the handler to go to the playground, and send a request.