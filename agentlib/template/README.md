# Weather agent with the agentlib

A minimal durable weather agent: [agent.ts](src/agent.ts) defines the model,
tool, and handler; [app.ts](src/app.ts) serves it. The weather tool returns
fixed demo data, so only an OpenAI API key is needed to run the agent.

## Run

Requires Node.js 22.21.1+ and the [agentlib setup](../README.md#setup).
From this directory:

```sh
npm install
export OPENAI_API_KEY=your-api-key
# Optional: export AGENT_MODEL=gpt-5.4
npm run dev
```

Start Restate in a second terminal:

```sh
npx @restatedev/restate-server
```

Register the app and invoke the agent through Restate:

```sh
npx @restatedev/restate deployments register http://localhost:9080
curl localhost:8080/agent/run --json '{"prompt":"What is the weather in San Francisco?"}'
```

Use `{}` to try the default prompt. Open http://localhost:9070 to inspect the
model and tool calls. Stop and restart the app during a request to see it
resume from its journal.

`asyncTool` validates arguments, journals results, and retries failed attempts.
Replace its demo implementation with an ordinary async weather API call.
The model has an explicit retry policy and the agent is bounded to five steps.
Each request starts a fresh conversation; see the
[conversation example](../examples/src/lessons/03_conversation.ts) for persistent sessions.

## Build and test

```sh
npm run build
npm run app
```

With Docker running, run `npm test` for an always-replay integration test. It
uses a fixture model, checks the weather tool result and final reply, and
verifies committed model calls are not repeated during replay. No API key is
needed for the test.

Continue with the [SDK examples](../examples/README.md).
