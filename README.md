<!-- markdown-link-check-disable -->
[![Documentation](https://img.shields.io/badge/doc-reference-blue)](https://docs.restate.dev)
[![Discord](https://img.shields.io/discord/1128210118216007792?logo=discord)](https://discord.restate.dev)
[![Slack](https://img.shields.io/badge/Slack-4A154B?logo=slack&logoColor=fff)](https://slack.restate.dev)
[![Twitter](https://img.shields.io/twitter/follow/restatedev.svg?style=social&label=Follow)](https://x.com/intent/follow?screen_name=restatedev)
<!-- markdown-link-check-enable -->

# Durable Agents and AI workflows with Restate

This repo contains a set of runnable examples of AI agents and workflows, using  **Durable Execution, state, and orchestration** via [Restate](https://restate.dev/) ([Github](https://github.com/restatedev/restate))

## Why Restate?

Restate is a durable runtime for agents and backends. It gives you:
- ✅ **Durable Execution**: Retry and recover from failures without repeating completed steps.
- ✅ **Durable Coroutines**: Run multiple tools, subagents, and sandbox commands in parallel with recovery and coordination.
- ✅ **State & session coordination**: Built-in multi-turn, persistent sessions. Scale out to thousands of concurrent sessions with built-in concurrency control
- ✅ **Communication & flow control**: Resiliently route tasks between distributed agents, humans, and MCP servers, and shape traffic with concurrency control
- ✅ **Observability & control**: Inspect detailed execution journals, and pause, cancel, kill, or roll back stuck agents
- ✅ **Production safety**: Approvals, timeouts, rollbacks, and escalation without callback plumbing


<img src="/doc/img/patterns/parallel_tools.png" alt="Restate UI - trace of agent with parallel tools" width="900px"/>
<br/>
<caption><em>Restate UI showing an agent execution with parallel tool calls</em></caption>

## How to build agents with Restate?
There are three ways to build durable agents with Restate. **We recommend the first two:**

1. **[agentlib](agentlib/examples/README.md)**: Start here for initial proofs of concept, simple agents, or any agent whose logic fits agentlib's abstractions.
2. **Custom / DIY**: Build directly on Restate when you need custom agent logic or more control. Use the **[agent reference architecture](https://github.com/restatedev/agent)** as a starting point.
3. **An agent SDK integration**: Use Restate with frameworks such as Vercel AI, OpenAI Agents, Google ADK, Pydantic AI, or LangChain. See the templates and examples below.

The reference architecture is also useful for agents built with agentlib: its patterns for session management, queuing, steering, interruption, and approvals can help you build the surrounding application.

## Using AI coding tools

The [Restate plugin](https://github.com/restatedev/skills) provides coding skills and the Restate docs MCP server. The repository root, all standalone templates, and the agentlib examples include configuration for [Claude Code](.claude/settings.json) and [Codex](.codex/config.toml). The [shared marketplace catalog](.agents/plugins/marketplace.json) points to the published plugin.

Codex enables the plugin after you trust the project. See the [plugin installation instructions](https://github.com/restatedev/skills#install-plugin) for details.


## Quickstart Templates

Restate integrates with popular Agent SDKs and with all LLM SDKs (only abstracting away the LLM API).

| Integration | Quickstart | Template |
| ------------------------------------ | ------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------- |
| **Restate agentlib** | [Setup](agentlib/template/README.md#run) | [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="24" height="24">](agentlib/template/README.md) |
| **TS DIY agents** | [📖](https://docs.restate.dev/ai-quickstart) | [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="24" height="24">](typescript-restate-only/template/README.md) |
| **Python DIY agents** | [📖](https://docs.restate.dev/ai-quickstart) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24">](python-restate-only/template/README.md) |
| **Vercel AI SDK** | [📖](https://docs.restate.dev/ai-quickstart) | [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="24" height="24">](vercel-ai/template/README.md) |
| **OpenAI Agents SDK** | [📖](https://docs.restate.dev/ai-quickstart) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24">](openai-agents/template/README.md) |
| **Google ADK** | [📖](https://docs.restate.dev/ai-quickstart) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24">](google-adk/template/README.md) |
| **Pydantic AI** | [📖](https://docs.restate.dev/ai-quickstart) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24">](pydantic-ai/template/README.md) |
| **LangChain** | [📖](https://docs.restate.dev/ai-quickstart) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24">](langchain-python/template/README.md) |


## Getting Started - Basic Examples

| Pattern | Docs | Restate agentlib | TS DIY agents | Python DIY agents | Vercel AI | OpenAI | ADK | Pydantic AI | LangChain |
| --------- | ------ | ----------- | --- | --- | ----------- | -------- | ----- | ------------- | ----------- |
| **Durable agents**: Build AI agents that survive crashes and recover automatically | [📖](https://docs.restate.dev/ai/patterns/durable-agents) | [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="24" height="24">](agentlib/template/src/agent.ts) | [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="24" height="24">](typescript-restate-only/template/src/agent.ts) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24">](python-restate-only/template/agent.py) | [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="24" height="24">](vercel-ai/template/src/app.ts) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24">](openai-agents/template/agent.py) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24">](google-adk/template/agent.py) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24">](pydantic-ai/template/agent.py) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24">](langchain-python/template/agent.py) |
| **Durable Sessions**: Persistent, isolated agent sessions | [📖](https://docs.restate.dev/ai/patterns/sessions) | [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="24" height="24">](agentlib/examples/src/lessons/03_conversation.ts) | [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="24" height="24">](typescript-restate-only/tour-of-agents/src/chat-agent.ts) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24">](python-restate-only/tour-of-agents/app/chat_agent.py) | [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="24" height="24">](vercel-ai/tour-of-agents/src/chat-agent.ts) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24">](openai-agents/tour-of-agents/app/chat_agent.py) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24">](google-adk/tour-of-agents/app/chat_agent.py) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24">](pydantic-ai/tour-of-agents/app/chat_agent.py) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24">](langchain-python/tour-of-agents/app/chat_agent.py) |
| **Human approvals with pause/resume**: Human approval steps that suspend execution | [📖](https://docs.restate.dev/ai/patterns/human-in-the-loop) | [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="24" height="24">](agentlib/examples/src/lessons/06_human_approval.ts) | [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="24" height="24">](typescript-restate-only/tour-of-agents/src/human-approval-agent.ts) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24">](python-restate-only/tour-of-agents/app/human_approval_agent.py) | [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="24" height="24">](vercel-ai/tour-of-agents/src/human-approval-agent.ts) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24">](openai-agents/tour-of-agents/app/human_approval_agent.py) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24">](google-adk/tour-of-agents/app/human_approval_agent.py) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24">](pydantic-ai/tour-of-agents/app/human_approval_agent.py) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24">](langchain-python/tour-of-agents/app/human_approval_agent.py) |
| **Multi-agent orchestration**: Route requests to specialized agents | [📖](https://docs.restate.dev/ai/patterns/multi-agent) | [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="24" height="24">](agentlib/examples/src/lessons/12_routing.ts) | [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="24" height="24">](typescript-restate-only/tour-of-agents/src/multi-agent.ts) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24">](python-restate-only/tour-of-agents/app/multi_agent.py) | [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="24" height="24">](vercel-ai/tour-of-agents/src/multi-agent.ts) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24">](openai-agents/tour-of-agents/app/multi_agent.py) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24">](google-adk/tour-of-agents/app/multi_agent.py) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24">](pydantic-ai/tour-of-agents/app/multi_agent.py) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24">](langchain-python/tour-of-agents/app/multi_agent.py) |

## Implementation Guides

### Orchestration Guides

| Pattern | Docs | Restate agentlib | TS DIY agents | Python DIY agents | Vercel AI | OpenAI | ADK | Pydantic AI | LangChain |
| ---------------------------------------------------------------------------------------------------------- | ------ | ----------- | --- | --- | ----------- | -------- | ----- | ------------- | ----------- |
| **Parallel tool calls**: Run multiple tools in parallel with recovery and coordination | [📖](https://docs.restate.dev/ai/patterns/parallelization) | [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="24" height="24">](agentlib/examples/src/lessons/08_research_report.ts) | [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="24" height="24">](typescript-restate-only/tour-of-agents/src/workflow-parallel.ts) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24">](python-restate-only/tour-of-agents/app/workflow_parallel.py) | [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="24" height="24">](vercel-ai/tour-of-agents/src/workflow-parallel.ts) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24">](openai-agents/tour-of-agents/app/workflow_parallel.py) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24">](google-adk/tour-of-agents/app/workflow_parallel.py) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24">](pydantic-ai/tour-of-agents/app/workflow_parallel.py) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24">](langchain-python/tour-of-agents/app/workflow_parallel.py) |
| **Sequential LLM calls**: Chain agents in multi-step pipelines | [📖](https://docs.restate.dev/ai/patterns/workflow-sequential) | [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="24" height="24">](agentlib/examples/src/lessons/15_peer_review_rpc.ts) | [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="24" height="24">](typescript-restate-only/tour-of-agents/src/workflow-sequential.ts) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24">](python-restate-only/tour-of-agents/app/workflow_sequential.py) | [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="24" height="24">](vercel-ai/tour-of-agents/src/workflow-sequential.ts) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24">](openai-agents/tour-of-agents/app/workflow_sequential.py) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24">](google-adk/tour-of-agents/app/workflow_sequential.py) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24">](pydantic-ai/tour-of-agents/app/workflow_sequential.py) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24">](langchain-python/tour-of-agents/app/workflow_sequential.py) |
| **Parallel agents**: Executing multiple agents in parallel | [📖](https://docs.restate.dev/ai/patterns/workflow-parallel) | [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="24" height="24">](agentlib/examples/src/lessons/08_research_report.ts) | [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="24" height="24">](typescript-restate-only/tour-of-agents/src/workflow-parallel.ts) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24">](python-restate-only/tour-of-agents/app/workflow_parallel.py) | [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="24" height="24">](vercel-ai/tour-of-agents/src/workflow-parallel.ts) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24">](openai-agents/tour-of-agents/app/workflow_sequential.py) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24">](google-adk/tour-of-agents/app/workflow_parallel.py) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24">](pydantic-ai/tour-of-agents/app/workflow_parallel.py) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24">](langchain-python/tour-of-agents/app/workflow_parallel.py) |
| **Orchestrator-worker**: Break tasks into specialized subtasks | [📖](https://docs.restate.dev/ai/patterns/workflow-orchestrator) | [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="24" height="24">](agentlib/examples/src/lessons/08_research_report.ts) | [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="24" height="24">](typescript-restate-only/tour-of-agents/src/workflow-orchestrator.ts) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24">](python-restate-only/tour-of-agents/app/workflow_orchestrator.py) | [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="24" height="24">](vercel-ai/tour-of-agents/src/workflow-orchestrator.ts) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24">](openai-agents/tour-of-agents/app/workflow_orchestrator.py) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24">](google-adk/tour-of-agents/app/workflow_orchestrator.py) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24">](pydantic-ai/tour-of-agents/app/workflow_orchestrator.py) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24">](langchain-python/tour-of-agents/app/workflow_orchestrator.py) |
| **Evaluator-optimizer**: Generate, evaluate, improve loop | [📖](https://docs.restate.dev/ai/patterns/workflow-evaluator) | [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="24" height="24">](agentlib/examples/src/lessons/05_evaluator_optimizer.ts) | [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="24" height="24">](typescript-restate-only/tour-of-agents/src/workflow-evaluator-optimizer.ts) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24">](python-restate-only/tour-of-agents/app/workflow_evaluator_optimizer.py) | [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="24" height="24">](vercel-ai/tour-of-agents/src/workflow-evaluator-optimizer.ts) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24">](openai-agents/tour-of-agents/app/workflow_evaluator_optimizer.py) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24">](google-adk/tour-of-agents/app/workflow_evaluator_optimizer.py) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24">](pydantic-ai/tour-of-agents/app/workflow_evaluator_optimizer.py) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24">](langchain-python/tour-of-agents/app/workflow_evaluator_optimizer.py) |
| **Workflows as tools**: Complex tool logic as separate durable services | [📖](https://docs.restate.dev/ai/patterns/tools) | [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="24" height="24">](agentlib/examples/src/lessons/10_service_tool.ts) | [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="24" height="24">](typescript-restate-only/tour-of-agents/src/parallel-tools-agent.ts) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24">](python-restate-only/tour-of-agents/app/parallel_tools_agent.py) | [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="24" height="24">](vercel-ai/tour-of-agents/src/parallel-tools-agent.ts) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24">](openai-agents/tour-of-agents/app/parallel_tools_agent.py) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24">](google-adk/tour-of-agents/app/parallel_tools_agent.py) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24">](pydantic-ai/tour-of-agents/app/parallel_tools_agent.py) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24">](langchain-python/tour-of-agents/app/parallel_tools_agent.py) |
| **Remote agents**: Deploy/scale agents separately with resilient RPC and queuing | [📖](https://docs.restate.dev/ai/patterns/remote-agents) | [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="24" height="24">](agentlib/examples/src/lessons/15_peer_review_rpc.ts) | [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="24" height="24">](typescript-restate-only/tour-of-agents/src/remote-agents.ts) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24">](python-restate-only/tour-of-agents/app/remote_agents.py) | [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="24" height="24">](vercel-ai/tour-of-agents/src/remote-agents.ts) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24">](openai-agents/tour-of-agents/app/remote_agents.py) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24">](google-adk/tour-of-agents/app/remote_agents.py) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24">](pydantic-ai/tour-of-agents/app/remote_agents.py) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24">](langchain-python/tour-of-agents/app/remote_agents.py) |
| **Competitive racing agents**: Run parallel agents, use the fastest response, cancel others | [📖](https://docs.restate.dev/ai/patterns/competitive-racing) | [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="24" height="24">](agentlib/examples/src/lessons/07_racing_agents.ts) | [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="24" height="24">](typescript-restate-only/tour-of-agents/src/racing-agents.ts) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24">](python-restate-only/tour-of-agents/app/racing_agents.py) | - | - | - | - | - |
| **Interrupt & regenerate**: Interrupt a running agent with new context; cancel in-flight task and restart | - | - | [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="24" height="24">](typescript-restate-only/examples/interrupt-regenerate/src/agent.ts) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24">](python-restate-only/examples/interrupt-regenerate/agent.py) | - | - | - | - | - |

### Reliability Guides

| Pattern | Docs | Restate agentlib | TS DIY agents | Python DIY agents | Vercel AI | OpenAI | ADK | Pydantic AI | LangChain |
| --------- | ------ | ----------- | --- | --- | ----------- | -------- | ----- | ------------- | ----------- |
| **Error handling**: Retries and error handling for agents | [📖](https://docs.restate.dev/ai/patterns/error-handling) | [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="24" height="24">](agentlib/examples/src/lessons/02_tools.ts) | - | - | [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="24" height="24">](vercel-ai/tour-of-agents/src/errorhandling) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24">](openai-agents/tour-of-agents/app/error_handling.py) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24">](google-adk/tour-of-agents/app/error_handling.py) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24">](pydantic-ai/tour-of-agents/app/error_handling.py) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24">](langchain-python/tour-of-agents/app/error_handling.py) |
| **Rollback**: Saga pattern for compensating failed operations | [📖](https://docs.restate.dev/ai/patterns/rollback) | - | - | - | [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="24" height="24">](vercel-ai/tour-of-agents/src/rollback-agent.ts) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24">](openai-agents/examples/rollback) | - | - | - |

### Frontend Integration

| Pattern | Docs | Restate agentlib | TS DIY agents | Python DIY agents | Vercel AI | OpenAI | ADK | Pydantic AI | LangChain |
| --------- | ------ | ----------- | --- | --- | ----------- | -------- | ----- | ------------- | ----------- |
| **Chat UI integration**: Integrate agents with chat UIs | [📖](https://docs.restate.dev/ai/patterns/chat-ui-integration) | - | - | - | [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="24" height="24">](vercel-ai/nextjs-example-app/README.md) | - | - | - | - |
| **Streaming responses**: Stream agent responses to clients | [📖](https://docs.restate.dev/ai/patterns/streaming-responses) | - | - | - | [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="24" height="24">](vercel-ai/nextjs-example-app/README.md) | - | - | - | - |
| **Notify when ready**: Callback when agent completes | [📖](https://docs.restate.dev/ai/patterns/notify-when-ready) | - | - | - | - | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24">](openai-agents/examples/notify_when_ready/agent.py) | - | - | - |


## Integrations

### Protocols
| Example                                                                                                                                                      | Code |
|--------------------------------------------------------------------------------------------------------------------------------------------------------------|------|
| **MCP**: Using Restate for exposing tools and resilient orchestration of tool calls                                                                          | [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="24" height="24">](mcp/README.md) |
| **A2A**: Implement Google's Agent-to-Agent protocol with Restate as resilient, scalable task orchestrator                                                    | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24">](a2a/README.md) |

### AI Observability

| Integration | Restate agentlib | TS DIY agents | Python DIY agents | OpenAI Agents | Google ADK | Pydantic AI |
| ---------------------- | ----------- | --- | --- | ------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Langfuse** | - | - | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="20" height="20">](python-restate-only/examples/langfuse/README.md) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="20" height="20">](openai-agents/examples/langfuse/README.md) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="20" height="20">](google-adk/examples/langfuse/README.md) | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="20" height="20">](pydantic-ai/examples/langfuse/README.md) |
| **Arize Phoenix** | - | - | - | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="20" height="20">](openai-agents/examples/arize_phoenix/README.md) | - | - |
| **Pydantic LogFire** | - | - | - | - | - | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="20" height="20">](pydantic-ai/examples/logfire/README.md) |
| **Braintrust** | - | [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="20" height="20">](typescript-restate-only/examples/braintrust/README.md) | - | - | - | - |

### Others

| Example                                                                                                                                                      | Code |
|--------------------------------------------------------------------------------------------------------------------------------------------------------------|------|
| **NextJS Template**: Minimal example of Restate + AI SDK + NextJS                                                                                            | [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="24" height="24">](vercel-ai/nextjs-template/README.md) |
| **NextJS Example App**: Example app of Restate + AI SDK + NextJS with tools, chat, pubsub,...                                                                | [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="24" height="24">](vercel-ai/nextjs-example-app/README.md) |

## Advanced Examples

Larger, end-to-end applications (in separate repos) showing how Restate holds up in real-world agentic systems.

| Example                                                                                                                                                      | Code |
|--------------------------------------------------------------------------------------------------------------------------------------------------------------|------|
| **Agent reference architecture**: Custom agents with session management, queuing, steering, interruption, approvals, and parallel tools and subagents | [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="24" height="24">](https://github.com/restatedev/agent) |
| **Coding agent**: orchestrates multi-turn conversations and coordinates subagents over sandboxed task execution                                              | [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="24" height="24">](https://github.com/igalshilman/agent47) |
| **Deep Research Agent**: Autonomous multi-day research agent (news digests, human-approved plans, parallel investigations) with Restate + LangChain + Tavily | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24">](https://github.com/gvdongen/resilient-research-agent) |
| **Supervisor Agent**: Supervisor pattern with policy gates, audit trails, and escalation ladders for security remediation workflows                          | [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="24" height="24">](https://github.com/gvdongen/resilient-supervisor-agent) |

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
