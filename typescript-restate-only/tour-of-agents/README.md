# Tour of AI Agents with Restate - TypeScript (no agent SDK)

A collection of examples showing how to build resilient AI agents with the [Restate TypeScript SDK](https://docs.restate.dev/develop/ts/overview) and [Vercel AI SDK](https://ai-sdk.dev/) for model calls, without using an agent framework. You manage the agent loop yourself with full control over execution.

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
| **Workflows as tools** | Complex tool logic as separate durable services | [📖](https://docs.restate.dev/ai/patterns/tools) | [parallel-tools-agent.ts](src/parallel-tools-agent.ts) |
| **Remote agents** | Deploy/scale agents separately with resilient RPC | [📖](https://docs.restate.dev/ai/patterns/remote-agents) | [remote-agents.ts](src/remote-agents.ts) |
| **Competitive racing** | Run parallel agents, use the fastest response | [📖](https://docs.restate.dev/ai/patterns/competitive-racing) | [racing-agents.ts](src/racing-agents.ts) |

## Run the examples

1. Export your OpenAI API key as an environment variable:
   ```shell
   export OPENAI_API_KEY=your_openai_api_key
   ```
2. [Start the Restate Server](https://docs.restate.dev/installation) in a separate shell:
   ```shell
   restate-server
   ```
3. Start the services:
   ```shell
   npm run dev
   ```
4. Register the services (use `--force` if you already had another deployment registered at 9080):
   ```shell
   restate -y deployments register localhost:9080 --force
   ```
5. In the UI, click on the handler to go to the playground, and send a request.
