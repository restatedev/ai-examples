# Tour of AI Agents with Restate - Vercel AI SDK

A collection of examples showing how to build resilient AI agents with the [Vercel AI SDK](https://ai-sdk.dev/) and [Restate](https://restate.dev/).

## Examples

| Pattern | Description | Docs | Code |
|---------|-------------|------|------|
| **Durable sessions** | Persistent, isolated agent sessions | [📖](https://docs.restate.dev/ai/patterns/sessions) | [chat-agent.ts](src/chat-agent.ts) |
| **Human approvals** | Human approval steps that suspend execution | [📖](https://docs.restate.dev/ai/patterns/human-in-the-loop) | [human-approval-agent.ts](src/human-approval-agent.ts) |
| **Human approvals with timeout** | Approvals with configurable timeout | [📖](https://docs.restate.dev/ai/patterns/human-in-the-loop) | [human-approval-agent-with-timeout.ts](src/human-approval-agent-with-timeout.ts) |
| **Multi-agent orchestration** | Route requests to specialized agents | [📖](https://docs.restate.dev/ai/patterns/multi-agent) | [multi-agent.ts](src/multi-agent.ts) |
| **Parallel tool calls** | Run multiple tools in parallel with recovery | [📖](https://docs.restate.dev/ai/patterns/parallelization) | [workflow-parallel.ts](src/workflow-parallel.ts) |
| **Sequential pipeline** | Chain agents in multi-step pipelines | [📖](https://docs.restate.dev/ai/patterns/workflows) | [workflow-sequential.ts](src/workflow-sequential.ts) |
| **Orchestrator-worker** | Break tasks into specialized subtasks | [📖](https://docs.restate.dev/ai/patterns/workflows) | [workflow-orchestrator.ts](src/workflow-orchestrator.ts) |
| **Evaluator-optimizer** | Generate, evaluate, improve loop | [📖](https://docs.restate.dev/ai/patterns/workflows) | [workflow-evaluator-optimizer.ts](src/workflow-evaluator-optimizer.ts) |
| **Workflows as tools** | Complex tool logic as separate durable services | [📖](https://docs.restate.dev/ai/patterns/tools) | [parallel-tools-agent.ts](src/parallel-tools-agent.ts), [sub-workflow-agent.ts](src/sub-workflow-agent.ts) |
| **Remote agents** | Deploy/scale agents separately with resilient RPC | [📖](https://docs.restate.dev/ai/patterns/remote-agents) | [remote-agents.ts](src/remote-agents.ts) |
| **Error handling** | Retries and error handling for agents | [📖](https://docs.restate.dev/ai/patterns/error-handling) | [errorhandling/](src/errorhandling) |
| **Rollback** | Saga pattern for compensating failed operations | [📖](https://docs.restate.dev/ai/patterns/rollback) | [rollback-agent.ts](src/rollback-agent.ts) |
| **MCP** | Agent with Model Context Protocol tools | - | [mcp-agent.ts](src/mcp-agent.ts) |

## Run the examples

[Install Restate](https://docs.restate.dev/installation) and launch it:

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
