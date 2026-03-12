<!-- markdown-link-check-disable -->
[![Documentation](https://img.shields.io/badge/doc-reference-blue)](https://docs.restate.dev)
[![Discord](https://img.shields.io/discord/1128210118216007792?logo=discord)](https://discord.restate.dev)
[![Slack](https://img.shields.io/badge/Slack-4A154B?logo=slack&logoColor=fff)](https://slack.restate.dev)
[![Twitter](https://img.shields.io/twitter/follow/restatedev.svg?style=social&label=Follow)](https://x.com/intent/follow?screen_name=restatedev)
<!-- markdown-link-check-enable -->

# Durable Agents and AI workflows with Restate

This repo contains a set of runnable examples of AI workflows and agents, using  **Durable Execution and Orchestration** via [Restate](https://restate.dev/) ([Github](https://github.com/restatedev/restate))

The goal is to show how you can easily add production-grade _resilience_, _state persistence_, _retries_, _suspend/resume_, _human-in-the-loop_, and _observability_ to agentic workflows. So you can ship agents that stay alive and consistent without sprinkling retry-code everywhere and without building heavyweight infra yourself.

The Restate approach works **independent of specific SDKs** but **integrates easily with popular SDKs**, like the [Vercel AI SDK](https://ai-sdk.dev/), the [OpenAI Agent SDK](https://openai.github.io/openai-agents-python/), and [Google ADK](https://google.github.io/adk-docs/). You can also use without any Agent SDK _(roll your own loop)_ or for more traditional workflows.


## Why Restate?

| Use Case                           | What it solves                                                                                       |
|------------------------------------|------------------------------------------------------------------------------------------------------|
| **Durable Execution**              | Crash-safe model and tool calls, idempotent retries, agents that resume at the last successful step. |
| **Detailed Observability**         | Auto-captured trace of every step, retry, and message for easy debugging and auditing.               |
| **Human-in-the-loop & long waits** | Suspend while waiting for user approval or slow jobs; pay for compute, not wall-clock time.          |
| **Stateful sessions / memory**     | Keep multi-turn conversations and other state isolated and consistent.                               |
| **Multi-agent orchestration**      | Reliable RPC, queuing, and scheduling between agents running in separate processes.                  |


<img src="/doc/img/patterns/parallel_tools.png" alt="Restate UI - trace of agent with parallel tools" width="900px"/>
<br/>
<caption><em>Restate UI showing an agent execution with parallel tool calls</em></caption>


## Quickstart Templates

| Integration                        | Quickstart                                           | Template                                                                                                             |
|------------------------------------|------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------|
| **Vercel AI SDK**                  | [📖](https://docs.restate.dev/ai-quickstart)         | [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="20" height="20">](vercel-ai/template/README.md)     |
| **OpenAI Agents SDK**              | [📖](https://docs.restate.dev/ai-quickstart)         | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="20" height="20">](openai-agents/template/README.md)       |
| **Google ADK**                     | [📖](https://docs.restate.dev/ai-quickstart)         | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="20" height="20">](google-adk/template/README.md)          |
| **Restate - Python - no agent SDK** | [📖](https://docs.restate.dev/ai-quickstart)         | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="20" height="20">](python-restate-only/template/README.md) |
| **Restate - TS - no agent SDK**    | [📖](https://docs.restate.dev/ai-quickstart)         | [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="20" height="20">](typescript-restate-only/template/README.md) |


## Getting Started - Basic Examples

| Pattern                               | Description | Docs | Restate | Vercel AI | OpenAI | ADK |
|---------------------------------------|-------------|------|---------|-----------|--------|-----|
| **Durable agents**                    | Build AI agents that survive crashes and recover automatically | [📖](https://docs.restate.dev/ai/patterns/durable-agents) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="20" height="20">](python-restate-only/template/agent.py) [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="20" height="20">](typescript-restate-only/template/src/agent.ts) | [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="20" height="20">](vercel-ai/template/src/app.ts) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="20" height="20">](openai-agents/template/agent.py) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="20" height="20">](google-adk/template/agent.py) |
| **Durable Sessions**                  | Persistent, isolated agent sessions | [📖](https://docs.restate.dev/ai/patterns/sessions) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="20" height="20">](python-restate-only/tour-of-agents/app/chat_agent.py) [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="20" height="20">](typescript-restate-only/tour-of-agents/src/chat-agent.ts) | [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="20" height="20">](vercel-ai/tour-of-agents/src/chat-agent.ts) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="20" height="20">](openai-agents/tour-of-agents/app/chat_agent.py) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="20" height="20">](google-adk/tour-of-agents/app/chat_agent.py) |
| **Human approvals with pause/resume** | Human approval steps that suspend execution | [📖](https://docs.restate.dev/ai/patterns/human-in-the-loop) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="20" height="20">](python-restate-only/tour-of-agents/app/human_approval_agent.py) [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="20" height="20">](typescript-restate-only/tour-of-agents/src/human-approval-agent.ts) | [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="20" height="20">](vercel-ai/tour-of-agents/src/human-approval-agent.ts) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="20" height="20">](openai-agents/tour-of-agents/app/human_approval_agent.py) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="20" height="20">](google-adk/tour-of-agents/app/human_approval_agent.py) |
| **Multi-agent orchestration**         | Route requests to specialized agents | [📖](https://docs.restate.dev/ai/patterns/multi-agent) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="20" height="20">](python-restate-only/tour-of-agents/app/multi_agent.py) [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="20" height="20">](typescript-restate-only/tour-of-agents/src/multi-agent.ts) | [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="20" height="20">](vercel-ai/tour-of-agents/src/multi-agent.ts) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="20" height="20">](openai-agents/tour-of-agents/app/multi_agent.py) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="20" height="20">](google-adk/tour-of-agents/app/multi_agent.py) |

## Implementation Guides

### Reliability Guides

| Pattern | Description | Docs | Restate | Vercel AI | OpenAI | ADK |
|---------|-------------|------|---------|-----------|--------|-----|
| **Error handling** | Retries and error handling for agents | [📖](https://docs.restate.dev/ai/patterns/error-handling) | - | [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="20" height="20">](vercel-ai/tour-of-agents/src/errorhandling) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="20" height="20">](openai-agents/tour-of-agents/app/error_handling.py) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="20" height="20">](google-adk/tour-of-agents/app/error_handling.py) |
| **Rollback** | Saga pattern for compensating failed operations | [📖](https://docs.restate.dev/ai/patterns/rollback) | - | [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="20" height="20">](vercel-ai/tour-of-agents/src/rollback-agent.ts) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="20" height="20">](openai-agents/examples/rollback) | - |

### Orchestration Guides

| Pattern                            | Description                                                   | Docs | Restate                                                                                                                                                                                                                                                                                                                       | Vercel AI                                                                                                                                        | OpenAI | ADK                                                                                                                                                   |
|------------------------------------|---------------------------------------------------------------|------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------|--------|-------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Parallel tool calls**            | Run multiple tools in parallel with recovery and coordination | [📖](https://docs.restate.dev/ai/patterns/parallelization) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="20" height="20">](python-restate-only/tour-of-agents/app/workflow_parallel.py) [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="20" height="20">](typescript-restate-only/tour-of-agents/src/workflow-parallel.ts)                       | [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="20" height="20">](vercel-ai/tour-of-agents/src/workflow-parallel.ts)            | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="20" height="20">](openai-agents/tour-of-agents/app/workflow_parallel.py) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="20" height="20">](google-adk/tour-of-agents/app/workflow_parallel.py)            |
| **Workflows: Sequential pipeline** | Chain agents in multi-step pipelines                          | [📖](https://docs.restate.dev/ai/patterns/workflows) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="20" height="20">](python-restate-only/tour-of-agents/app/workflow_sequential.py) [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="20" height="20">](typescript-restate-only/tour-of-agents/src/workflow-sequential.ts)                   | [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="20" height="20">](vercel-ai/tour-of-agents/src/workflow-sequential.ts)          | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="20" height="20">](openai-agents/tour-of-agents/app/workflow_sequential.py) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="20" height="20">](google-adk/tour-of-agents/app/workflow_sequential.py)          |
| **Workflows: Parallel agents**     | Executing multiple agents in parallel                         | [📖](https://docs.restate.dev/ai/patterns/workflows) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="20" height="20">](python-restate-only/tour-of-agents/app/workflow_parallel.py) [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="20" height="20">](typescript-restate-only/tour-of-agents/src/workflow-parallel.ts)                       | [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="20" height="20">](vercel-ai/tour-of-agents/src/workflow-parallel.ts)            | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="20" height="20">](openai-agents/tour-of-agents/app/workflow_sequential.py) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="20" height="20">](google-adk/tour-of-agents/app/workflow_parallel.py)            |
| **Workflows: Orchestrator-worker** | Break tasks into specialized subtasks                         | [📖](https://docs.restate.dev/ai/patterns/workflows) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="20" height="20">](python-restate-only/tour-of-agents/app/workflow_orchestrator.py) [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="20" height="20">](typescript-restate-only/tour-of-agents/src/workflow-orchestrator.ts)               | [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="20" height="20">](vercel-ai/tour-of-agents/src/workflow-orchestrator.ts)        | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="20" height="20">](openai-agents/tour-of-agents/app/workflow_orchestrator.py) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="20" height="20">](google-adk/tour-of-agents/app/workflow_orchestrator.py)        |
| **Workflows: Evaluator-optimizer** | Generate, evaluate, improve loop                              | [📖](https://docs.restate.dev/ai/patterns/workflows) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="20" height="20">](python-restate-only/tour-of-agents/app/workflow_evaluator_optimizer.py) [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="20" height="20">](typescript-restate-only/tour-of-agents/src/workflow-evaluator-optimizer.ts) | [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="20" height="20">](vercel-ai/tour-of-agents/src/workflow-evaluator-optimizer.ts) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="20" height="20">](openai-agents/tour-of-agents/app/workflow_evaluator_optimizer.py) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="20" height="20">](google-adk/tour-of-agents/app/workflow_evaluator_optimizer.py) |
| **Workflows as tools**             | Complex tool logic as separate durable services               | [📖](https://docs.restate.dev/ai/patterns/tools) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="20" height="20">](python-restate-only/tour-of-agents/app/parallel_tools_agent.py) [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="20" height="20">](typescript-restate-only/tour-of-agents/src/parallel-tools-agent.ts)                 | [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="20" height="20">](vercel-ai/tour-of-agents/src/parallel-tools-agent.ts)         | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="20" height="20">](openai-agents/tour-of-agents/app/parallel_tools_agent.py) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="20" height="20">](google-adk/tour-of-agents/app/parallel_tools_agent.py)         |
| **Remote agents**                  | Deploy/scale agents separately with resilient RPC and queuing | [📖](https://docs.restate.dev/ai/patterns/remote-agents) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="20" height="20">](python-restate-only/tour-of-agents/app/remote_agents.py) [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="20" height="20">](typescript-restate-only/tour-of-agents/src/remote-agents.ts)                               | [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="20" height="20">](vercel-ai/tour-of-agents/src/remote-agents.ts)                | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="20" height="20">](openai-agents/tour-of-agents/app/remote_agents.py) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="20" height="20">](google-adk/tour-of-agents/app/remote_agents.py)                |
| **Competitive racing agents**      | Run parallel agents, use the fastest response, cancel others  | [📖](https://docs.restate.dev/ai/patterns/competitive-racing) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="20" height="20">](python-restate-only/tour-of-agents/app/racing_agents.py) [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="20" height="20">](typescript-restate-only/tour-of-agents/src/racing-agents.ts)                               | -                                                                                                                                                | - | -                                                                                                                                                     |

### Frontend Integration

| Pattern | Description | Docs | Restate | Vercel AI | OpenAI                                                                                                                                    | ADK |
|---------|-------------|------|---------|-----------|-------------------------------------------------------------------------------------------------------------------------------------------|-----|
| **Chat UI integration** | Integrate agents with chat UIs | [📖](https://docs.restate.dev/ai/patterns/chat-ui-integration) | - | [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="20" height="20">](vercel-ai/nextjs-example-app/README.md) | -                                                                                                                                         | - |
| **Streaming responses** | Stream agent responses to clients | [📖](https://docs.restate.dev/ai/patterns/streaming-responses) | - | [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="20" height="20">](vercel-ai/nextjs-example-app/README.md) | -                                                                                                                                         | - |
| **Notify when ready** | Callback when agent completes | [📖](https://docs.restate.dev/ai/patterns/notify-when-ready) | - | - | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="20" height="20">](openai-agents/examples/notify_when_ready/agent.py) | - |


## More Examples

| Example                | Description                                                                                     | Code                                                                                                                    |
|------------------------|-------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------|
| **NextJS Template**    | Minimal example of Restate + AI SDK + NextJS                                                    | [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="20" height="20">](vercel-ai/nextjs-template/README.md) |
| **NextJS Example App** | Example app of Restate + AI SDK + NextJS with tools, chat, pubsub,...                           | [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="20" height="20">](vercel-ai/nextjs-example-app/README.md)        |
| **MCP**                | Using Restate for exposing tools and resilient orchestration of tool calls                       | [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="20" height="20">](mcp/README.md)                                 |
| **A2A**                | Implement Google's Agent-to-Agent protocol with Restate as resilient, scalable task orchestrator | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="20" height="20">](a2a/README.md)                             |


## Supported Languages

Restate currently supports 6 languages:

[![TypeScript](https://skillicons.dev/icons?i=ts)](https://docs.restate.dev/develop/ts/overview)
[![Python](https://skillicons.dev/icons?i=python&theme=light)](https://docs.restate.dev/develop/python/overview)
[![Java](https://skillicons.dev/icons?i=java&theme=light)](https://docs.restate.dev/develop/java/overview)
[![Kotlin](https://skillicons.dev/icons?i=kotlin&theme=light)](https://docs.restate.dev/develop/java/overview)
[![Go](https://skillicons.dev/icons?i=go)](https://docs.restate.dev/develop/go/overview)
[![Rust](https://skillicons.dev/icons?i=rust&theme=light)](https://docs.rs/restate-sdk/latest/restate_sdk/)

The examples can be translated to any of the supported languages.
Join our [Discord](https://discord.restate.dev)/[Slack](https://slack.restate.dev) to get help with translating an examples to your language of choice.

## Learn more
- [AI Documentation](https://docs.restate.dev/ai)
- [Examples on workflows, microservice orchestration, async tasks, event processing](https://github.com/restatedev/examples)
- [Restate Cloud](https://restate.dev/cloud/)
- [Discord](https://discord.restate.dev) / [Slack](https://slack.restate.dev)