# Resilient agents with Restate + Vercel AI SDK
[<img src="https://raw.githubusercontent.com/restatedev/img/refs/heads/main/show-code.svg">](src/app.ts)

Use the Vercel AI SDK to implement your agent, and let Restate handle the persistence and resiliency of the agent's decisions and tool executions.

The example is an agent that can search for the weather in certain city.

<img src="img/invocations_ui_vercel.png" alt="Using Agent SDK - journal" width="1200px"/>

> Also check out the advanced example in the [agents/vercel-ai](../../agents/vercel-ai/README.md) 

## Running the example

1. Export your OpenAI or Anthrophic API key as an environment variable:
    ```shell
    export OPENAI_API_KEY=your_openai_api_key
    ```
2. [Start the Restate Server](https://docs.restate.dev/develop/local_dev) in a separate shell:
    ```shell
    npx @restatedev/restate-server@latest
    ```
3. Start the services:
    ```shell
    npm install
    npm run app-dev
    ```
4. Register the services:
    ```shell
    restate -y deployments register localhost:9080
    ```

5. Send requests to your agent:

    ```shell
    curl localhost:8080/Agent/run --json '"What is the weather in Detroit?"'
    ```

   Returns: `The weather in Detroit is currently 22°C and sunny.`


Check the Restate UI (`http://localhost:9080`) to see the journals of your invocations (remove the filters).

<img src="img/journal_vercel.png" alt="Using Agent SDK - journal" width="1200px"/>


## Integrating Restate with the Vercel AI SDK

To make the agent resilient, we need to:
- Persist the results of LLM calls in Restate's journal by wrapping them in `ctx.run()`. This is handled by the `durableCalls` middleware for the model.
- To persist the intermediate tool execution steps, we use the Restate context.

## Limitations
1. You cannot do parallel tool calls or any type of parallel execution if you integrate Restate with an Agent SDK.
If you execute actions on the context in different tools in parallel, Restate will not be able to deterministically replay them because the order might be different during recovery and will crash.
We are working on a solution to this, but for now, you can only use Restate with Agent SDKs for sequential tool calls.

2. Restate does not yet support streaming responses from the Vercel AI SDK.