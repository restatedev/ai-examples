# Restate TypeScript Agent + Braintrust tracing

A template for creating a Restate agent in TypeScript that emits traces to Braintrust.

## Run the example

[Install Restate](https://docs.restate.dev/installation) and launch it:

```bash
npm install --global @restatedev/restate-server@latest @restatedev/restate@latest
```

Create a Restate configuration file `restate.toml`:

```toml
tracing-endpoint="otlp+https://api.braintrust.dev/otel/v1/traces"

[tracing-headers]
authorization="Bearer your-braintrust-api-key"
x-bt-parent="project_id:your-project-id"
```

Then run Restate with the configuration file:

```shell
restate-server --config-file restate.toml
```

Get the example:

```bash
restate example typescript-restate-agent && cd typescript-restate-agent
npm install
```

Export your [OpenAI API key](https://platform.openai.com/api-keys) and run the agent:

```bash
export BRAINTRUST_API_KEY=sk-...
export BRAINTRUST_PROJECT_ID=...
export OPENAI_API_KEY=sk-...
npm run dev
```

Register the agent with Restate via the UI or CLI:

```bash
restate deployments register http://localhost:9080 --force --yes
```

Go to the Restate UI `localhost:9070` and click on your handler to run it via the playground.
