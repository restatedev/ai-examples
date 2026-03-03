# Tour of AI Agents with Restate - Vercel AI SDK

Learn how to implement resilient agents with durable execution, human-in-the-loop, multi-agent communication, and parallel execution.

## Run the example

[Install Restate](/installation) and launch it:

```bash
npm install --global @restatedev/restate-server@latest @restatedev/restate@latest
restate-server
```

Get the example:

```bash
restate example typescript-vercel-ai-tour-of-agents && cd typescript-vercel-ai-tour-of-agents
npm install
```

Export your [OpenAI API key](https://platform.openai.com/api-keys) and run the agent:

```bash
export OPENAI_API_KEY=sk-...
npx tsx src/durable-agent.ts
```

Change the path to the agent you want to run.

Register the agents with Restate:

```bash
restate deployments register http://localhost:9080 --force --yes
```
