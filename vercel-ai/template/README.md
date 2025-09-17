# Restate + Vercel AI Example (non-NextJS)

This is template of a simple agent written with the Vercel AI SDK and using Restate for resilience and observability.

This example is for deployments where the agent is served directly, and not as part of a NextJS app.
Use this template when deploying the agent on generic containers, FaaS (Lambda, Fly.io, etc.) or for simply experimenting locally.

## Running the template example

1. Export your OpenAI key as an environment variable. If you want to use another model (e.g., Anthrophic Claude, Google Gemini) you need to change the dependencies in `package.json` and the model in `src/app.ts` accordingly:
    ```shell
    export OPENAI_API_KEY=your_openai_api_key
    ```
2. [Start the Restate Server](https://docs.restate.dev/develop/local_dev) in a separate shell. The server is the durable orchstrator. It is queue, workflow engine, K/V store in one.
    ```shell
    npx @restatedev/restate-server@latest
    ```
3. Start the agent.
    ```shell
    npm install
    npm run dev
    ```
4. Register the services, to let Restate Server know about the agent. The Server can now proxy invocations to the agent, adding durable execution that way.
    ```shell
    npx @restatedev/restate -y deployments register localhost:9080
    ```

5. All should be ready. Now send a request to your agent. Note that we target Restate Server's endpoint (8080) because the server proxies requests to the service, to make them durable.

    ```shell
    curl localhost:8080/agent/run --json '"What is the weather in Detroit?"'
    ```

   Returns: `The weather in Detroit is currently 22°C and sunny.`

Check the Restate UI (`localhost:9080`) to see the journals of your invocations.

<img src="https://raw.githubusercontent.com/restatedev/ai-examples/refs/heads/main/doc/img/get-started-vercel/journal_vercel.png" alt="Using Agent SDK - journal" width="1200px"/>