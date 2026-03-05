# Restate Agent Template - TypeScript

A template for creating a Restate agent in TypeScript.

## Run the example

[Install Restate](/installation) and launch it:

```bash
npm install --global @restatedev/restate-server@latest @restatedev/restate@latest
restate-server
```

Get the example:

```bash
restate example typescript-restate-agent && cd typescript-restate-agent
npm install
```

Export your [OpenAI API key](https://platform.openai.com/api-keys) and run the agent:

```bash
export OPENAI_API_KEY=sk-...
npm run dev
```

Register the agent with Restate via the UI or CLI:

```bash
restate deployments register http://localhost:9080 --force --yes
```

Go to the Restate UI `localhost:9070` and click on your handler to run it via the playground.