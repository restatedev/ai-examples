# Restate + Vercel AI Example (for NextJS)

This is template of a simple agent, written with the Vercel AI SDK and using Restate for resilience and observability.
It set up as a NextJS app.

Use this template when deploying the agent as a NextJS app, for example on Vercel. For deployments on other stacks, use the standard template, which serves the agent services via HTTP/2 (fastest option) or runs on FaaS like AWS Lambda natively.  

## Running the template example

1. Install all dependencies
    ```shell
    npm install
    ```
2. Export your OpenAI key as an environment variable. If you want to use another model (e.g., Anthrophic Claude, Google Gemini) you need to change the dependencies in `package.json` and the model in `restate/services/agent.ts` accordingly:
    ```shell
    export OPENAI_API_KEY=your_openai_api_key
    ```
3. Start the nextjs app, which contains the agent code.
    ```shell
    npm run dev
    ```

4. [Start the Restate Server](https://docs.restate.dev/develop/local_dev) in a separate shell. The server is the durable orchstrator. It is queue, workflow engine, k/V store in one.
    ```shell
    npx @restatedev/restate-server@latest
    ```

5. Register the services, to let Restate Server know about the agent. The Server can now proxy invocations to the agent, adding durable execution that way. You can do this via the UI (by default at `http://localhost:9070`)
    ```shell
    npx @restatedev/restate deployments register -y --use-http1.1 http://localhost:3000/restate/v1
    ```

6. All should be ready. Now send a request to your agent. You can do that through the UI, or via HTTP. _(note that we target Restate Server's endpoint (8080) because the server proxies requests to the service, to make them durable.)_

    ```shell
    curl localhost:8080/agent/run --json '"What is the weather in Detroit?"'
    ```

   Returns: `The weather in Detroit is currently 22°C and sunny.`

Check the Restate UI (`localhost:9070`) to see the journals of your invocations.