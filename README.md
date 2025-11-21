<!-- markdown-link-check-disable -->
[![Documentation](https://img.shields.io/badge/doc-reference-blue)](https://docs.restate.dev)
[![Discord](https://img.shields.io/discord/1128210118216007792?logo=discord)](https://discord.gg/skW3AZ6uGd)
[![Slack](https://img.shields.io/badge/Slack-4A154B?logo=slack&logoColor=fff)](https://join.slack.com/t/restatecommunity/shared_invite/zt-2v9gl005c-WBpr167o5XJZI1l7HWKImA)
[![Twitter](https://img.shields.io/twitter/follow/restatedev.svg?style=social&label=Follow)](https://x.com/intent/follow?screen_name=restatedev)
<!-- markdown-link-check-enable -->

# Examples for AI workflows and Durable Agents

This repo contains a set of runnable examples of AI workflows and agents, using  **Durable Execution and Orchestration** via [Restate](https://restate.dev/) ([Github](https://github.com/restatedev/restate))

The goal is to show how you can easily add production-grade _resilience_, _state persistence_, _retries_, _suspend/resume_, _human-in-the-loop_, and _observability_ to agentic workflows. So you can ship agents that stay alive and consistent without sprinkling retry-code everywhere and without building heavyweight infra yourself.

The Restate approach works **independent of specific SDKs** but **integrates easily with popular SDKs**, like the [Vercel AI SDK](https://ai-sdk.dev/) or the [OpenAI Agent SDK](https://openai.github.io/openai-agents-python/). You can also use without and Agent SDK _(roll your own loop)_ or for more traditional workflows.


## Why Restate?
📄 For a gentle intro, read [the blog post "Durable Agents - Fault Tolerance across Frameworks and without Handcuffs"](https://restate.dev/blog/durable-ai-loops-fault-tolerance-across-frameworks-and-without-handcuffs/)


| Use Case                           | What it solves                                                                              |
|------------------------------------|---------------------------------------------------------------------------------------------|
| **Durable Execution**              | Crash-safe LLM/tool calls & idempotent retries—agents resume at the last successful step.   |
| **Detailed Observability**         | Auto-captured trace of every step, retry, and message for easy debugging and auditing.      |
| **Human-in-the-loop & long waits** | Suspend while waiting for user approval or slow jobs; pay for compute, not wall-clock time. |
| **Stateful sessions / memory**     | Virtual Objects keep multi-turn conversations and other state isolated and consistent.      |
| **Multi-agent orchestration**      | Reliable RPC, queuing, and scheduling between agents running in separate processes.         |


<img src="/doc/img/patterns/parallel_tools.png" alt="Restate UI - trace of agent with parallel tools" width="900px"/>
<br/>
<caption><em>Restate UI showing an agent execution with parallel tool calls</em></caption>


## Full Example Catalog

### Agent SDK Integrations  
| Integration | Example | Description | Code | Docs                                                 |
|-------------|---------|-------------|------|------------------------------------------------------|
| **Vercel AI SDK** | **Template** | A minimal example of how to use Restate with the Vercel AI SDK | [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="20" height="20">](vercel-ai/template) | [📖](https://docs.restate.dev/ai-quickstart)         |
| | **Tour of Agents** | A step-by-step tutorial showing how to build resilient agents | [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="20" height="20">](vercel-ai/tour-of-agents) | [📖](https://docs.restate.dev/tour/vercel-ai-agents) |
| | **Examples** | More advanced examples that can be deployed as a Next.js app on Vercel | [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="20" height="20">](vercel-ai/examples) | -                                                    |
| **OpenAI Agents SDK** | **Template** | A minimal example of how to use Restate with the OpenAI Agents SDK | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="20" height="20">](openai-agents/template) | [📖](https://docs.restate.dev/ai-quickstart)         |
| | **Tour of Agents** | A step-by-step tutorial showing how to build resilient agents | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="20" height="20">](openai-agents/tour-of-agents) | [📖](https://docs.restate.dev/tour/openai-agents)    |

### Composable AI Patterns
| Pattern                | Description | Code | Docs |
|------------------------|-------------|------|------|
| **Chaining LLM calls** | Build fault-tolerant processing pipelines where each step transforms the previous step's output | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="20" height="20">](python-patterns/app/chaining.py) [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="20" height="20">](typescript-patterns/src/chaining.ts) | [📖](https://docs.restate.dev/ai/patterns/prompt-chaining) |
| **Tool routing** | Automatically route requests to tools based on LLM outputs | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="20" height="20">](python-patterns/app/routing_to_tool.py) [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="20" height="20">](typescript-patterns/src/routing-to-tools.ts) | [📖](https://docs.restate.dev/ai/patterns/tools) |
| **Parallel tool execution** | Execute multiple tools in parallel with durable results that persist across failures | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="20" height="20">](python-patterns/app/parallel_tools.py) [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="20" height="20">](typescript-patterns/src/parallel-tools.ts) | [📖](https://docs.restate.dev/ai/patterns/parallelization) |
| **Multi-agent routing** | Route requests to specialized agents based on LLM outputs | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="20" height="20">](python-patterns/app/routing_to_agent.py) [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="20" height="20">](typescript-patterns/src/routing-to-agent.ts) | [📖](https://docs.restate.dev/ai/patterns/multi-agent) |
| **Remote agent routing** | Deploy/scale agents separately and route requests with resilient communication | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="20" height="20">](python-patterns/app/routing_to_remote_agent.py) [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="20" height="20">](typescript-patterns/src/routing-to-remote-agent.ts) | [📖](https://docs.restate.dev/ai/patterns/multi-agent) |
| **Parallel agent processing** | Run multiple, specialized agents in parallel and aggregate their results | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="20" height="20">](python-patterns/app/parallel_agents.py) [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="20" height="20">](typescript-patterns/src/parallel-agents.ts) | [📖](https://docs.restate.dev/ai/patterns/parallelization) |
| **Racing agents** | Race multiple agents against each other and use the fastest response | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="20" height="20">](python-patterns/app/racing_agents.py) [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="20" height="20">](typescript-patterns/src/racing-agents.ts) | [📖](https://docs.restate.dev/ai/patterns/competitive-racing) |
| **Human-in-the-loop pattern** | Implement resilient human approval steps that suspend execution until feedback is received | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="20" height="20">](python-patterns/app/human_in_the_loop.py) [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="20" height="20">](typescript-patterns/src/human-in-the-loop.ts) | [📖](https://docs.restate.dev/ai/patterns/human-in-the-loop) |
| **Chat sessions** | Long-lived, stateful chat sessions that maintain conversation state across multiple requests | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="20" height="20">](python-patterns/app/chat.py) [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="20" height="20">](typescript-patterns/src/chat.ts) | [📖](https://docs.restate.dev/ai/patterns/sessions-and-chat) |
| **Orchestrator-worker pattern** | Break down complex tasks into specialized subtasks and execute them in parallel | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="20" height="20">](python-patterns/app/orchestrator_workers.py) | - |
| **Evaluator-optimizer pattern** | Generate → Evaluate → Improve loop until quality criteria are met | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="20" height="20">](python-patterns/app/evaluator_optimizer.py) [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="20" height="20">](typescript-patterns/src/evaluator-optimizer.ts) | - |

### Other Examples
| Example                | Description | Code |
|------------------------|-------------|------|
| **MCP**                |  Using Restate for exposing tools and resilient orchestration of tool calls | [<img src="https://skillicons.dev/icons?i=ts&theme=light" width="20" height="20">](mcp) | 
| **A2A**                | Implement Google's Agent-to-Agent protocol with Restate as resilient, scalable task orchestrator | [<img src="https://skillicons.dev/icons?i=python&theme=light" width="20" height="20">](a2a) | 

Restate currently supports 6 languages:

[![TypeScript](https://skillicons.dev/icons?i=ts)](https://docs.restate.dev/develop/ts/overview)
[![Python](https://skillicons.dev/icons?i=python&theme=light)](https://docs.restate.dev/develop/python/overview)
[![Java](https://skillicons.dev/icons?i=java&theme=light)](https://docs.restate.dev/develop/java/overview)
[![Kotlin](https://skillicons.dev/icons?i=kotlin&theme=light)](https://docs.restate.dev/develop/java/overview)
[![Go](https://skillicons.dev/icons?i=go)](https://docs.restate.dev/develop/go/overview)
[![Rust](https://skillicons.dev/icons?i=rust&theme=light)](https://docs.rs/restate-sdk/latest/restate_sdk/)

The examples can be translated to any of the supported languages. 
Join our [Discord](https://discord.gg/skW3AZ6uGd)/[Slack](https://join.slack.com/t/restatecommunity/shared_invite/zt-2v9gl005c-WBpr167o5XJZI1l7HWKImA) to get help with translating an examples to your language of choice.

## Learn more
- [Documentation](https://docs.restate.dev/ai)
- [Examples on workflows, microservice orchestration, async tasks, event processing](https://github.com/restatedev/examples)
- [Restate Cloud](https://restate.dev/cloud/)
- [Discord](https://discord.gg/skW3AZ6uGd) / [Slack](https://join.slack.com/t/restatecommunity/shared_invite/zt-2v9gl005c-WBpr167o5XJZI1l7HWKImA)

## Acknowledgements

- The DIY patterns are largely based on Anthropic's [agents cookbook](https://github.com/anthropics/anthropic-cookbook/tree/main/patterns/agents).
- Some of the A2A examples in this repo are based on the examples included in the [Google A2A repo](https://github.com/google/A2A/tree/main).
