# Weather agent with agentlib

A minimal weather agent using the agentlib library.

## Run

Requires Node.js 22.21.1+ and an OpenAI API key.
From this directory:

```sh
npm install
export OPENAI_API_KEY=your-api-key
# Optional: export AGENT_MODEL=gpt-5.4
npm run dev
```

[Install Restate](https://docs.restate.dev/installation) and launch it:

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
