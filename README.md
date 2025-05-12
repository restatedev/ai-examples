<!-- markdown-link-check-disable -->
[![Documentation](https://img.shields.io/badge/doc-reference-blue)](https://docs.restate.dev)
[![Discord](https://img.shields.io/discord/1128210118216007792?logo=discord)](https://discord.gg/skW3AZ6uGd)
[![Slack](https://img.shields.io/badge/Slack-4A154B?logo=slack&logoColor=fff)](https://join.slack.com/t/restatecommunity/shared_invite/zt-2v9gl005c-WBpr167o5XJZI1l7HWKImA)
[![Twitter](https://img.shields.io/twitter/follow/restatedev.svg?style=social&label=Follow)](https://x.com/intent/follow?screen_name=restatedev)
<!-- markdown-link-check-enable -->

# Restate: a next-gen runtime for robust, stateful, production-grade agents 

[Restate](https://ai.restate.dev/) lets you build **reliable, stateful AI agents** that work consistently in production. Move beyond fragile demos by giving your agents **innate resilience**—persistent memory, fault-tolerant tool/LLM calls, and robust handling of long-running tasks. Focus on your agent's intelligence, not the infrastructure complexity tax.

## Why Restate?

Restate provides the following capabilities:
- 🚀 **Move fast and far** - Innate resiliency and control from your first LLM-SDK-based app to low-level, customized multi-agent applications.
- ✅ **Resilience where it matters most** – Automatically recover from failures in your agentic workflows and tools.
- 🎮 **Task control** - Cancel tasks, query status, re-subscribe to ongoing tasks, and track progress across failures, time, and processes.
- 🤖 **Reliable multi-agent** - Flexible and reliable communication patterns including RPC, scheduled tasks, events, human-in-the-loop and parallel execution.
- 👀 **Full observability** – Line-by-line execution tracking with a built-in audit trail and UI. Seamless integration with OpenTelemetry.
- 🔁 **Orchestrate long-running processes** – Coordinate durable and stateful agentic processes for millis or months.
- 🔧 **Rich primitives** – Leverage workflows, durable promises, communication, and persistent state.
- 🧠 **Exactly-once execution** - Automatic deduplication of hand-offs and tool executions via idempotency keys.
- 💾 **Persistent memory** - Maintain consistent agent memory across infrastructure events.
- 🌍 **Deploy anywhere** – Whether it's AWS Lambda, CloudRun, Fly.io, Cloudflare, Kubernetes, Deno Deploy,...
- ☁️ **Easy to self-host** – Single-binary self-hosted deployments or connect to [Restate Cloud](https://restate.dev/cloud/).

Restate can also be used for other use cases, such as: 
[workflows](https://docs.restate.dev/use-cases/workflows),
[microservice orchestration](https://docs.restate.dev/use-cases/microservice-orchestration),
[async tasks](https://docs.restate.dev/use-cases/async-tasks), 
and [event processing](https://docs.restate.dev/use-cases/event-processing).

This repository contains examples of how to use Restate for AI / Agent use cases.


## Example catalog

1. [**DIY patterns**](diy-patterns): patterns for hardening custom LLM orchestration logic:
2. [**Agents**](agents): Using Restate (optionally with Agent SDKs) for resilient agentic workflows.
3. [**MCP**](mcp): Using Restate for exposing tools and resilient orchestration of tool calls.
4. [**A2A**](a2a): Implement Google's Agent-to-Agent protocol with Restate as resilient, scalable task orchestrator.
5. [**End-to-end applications**](end-to-end-applications): full-fledged examples of agentic Restate applications
   - [Mixing static, code-defined workflows with agentic workflows](end-to-end-applications/insurance-workflows)
   - [Long-lived multi-agent setups](end-to-end-applications/long-lived-agents)


Restate supports 6 languages:

[![TypeScript](https://skillicons.dev/icons?i=ts)](typescript)
[![Python](https://skillicons.dev/icons?i=python&theme=light)](python)
[![Java](https://skillicons.dev/icons?i=java&theme=light)](java)
[![Kotlin](https://skillicons.dev/icons?i=kotlin&theme=light)](kotlin)
[![Go](https://skillicons.dev/icons?i=go)](go)
[![Rust](https://skillicons.dev/icons?i=rust&theme=light)](rust)

The examples can be translated to any of the supported languages. 
Join our [Discord](https://discord.gg/skW3AZ6uGd)/[Slack](https://join.slack.com/t/restatecommunity/shared_invite/zt-2v9gl005c-WBpr167o5XJZI1l7HWKImA) to get help with translating an examples to your language of choice.

## Running the examples

Clone the repository and consult the README of the example you want to run for further instructions.

```bash
git clone git@github.com:restatedev/restate-ai-examples.git
```

## How Restate Compares (vs. Alternatives for Agents):

- **vs. DIY (Basic Loops + DB/Queue)**: Eliminates vast amounts of boilerplate code for retries, state management, consistency checks, and failure recovery that developers would otherwise need to build manually.
- **vs. Basic Agent Frameworks (focused on prompts/reasoning)**: Provides the crucial missing layer of execution reliability, state persistence, and robust async operation management needed for production. Restate complements these frameworks by providing a reliable runtime beneath the agent's reasoning logic.
- **vs. Heavy Workflow Engines:** Offers similar strong execution guarantees but with a lighter footprint, lower latency, simpler programming model (Virtual Objects), native serverless integration, and easier self-hosting/operational story—often a better fit for the potentially high-volume, interactive nature of agent applications.

## Learn more
- [Documentation](https://docs.restate.dev/)
- [Quickstart](https://docs.restate.dev/get_started/quickstart)
- [Tour of Restate: a tutorial including the most important features](https://docs.restate.dev/get_started/tour)
- [Examples on workflows, microservice orchestration, async tasks, event processing](https://github.com/restatedev/examples)
- [Restate Cloud](https://restate.dev/cloud/)
- [Discord](https://discord.gg/skW3AZ6uGd) / [Slack](https://join.slack.com/t/restatecommunity/shared_invite/zt-2v9gl005c-WBpr167o5XJZI1l7HWKImA)

## Disclaimers and acknowledgements

**Disclaimer 1**: The implementations of the agent loops in this repo are heavily inspired by the [OpenAI Agents SDK](https://github.com/openai/openai-agents-python). 
We therefore want to give credit to the developers of this SDK for the great work they have done.
This repo builds further on their work to make it benefit from Restate's programming model and capabilities.

**Disclaimer 2**: Many of the DIY patterns have been based on Anthropic's [agents cookbook](https://github.com/anthropics/anthropic-cookbook/tree/main/patterns/agents).

**Disclaimer 3**: The chat UI code in the `tooling/chat-ui` folder was generated by [v0 by Vercel](https://v0.dev/). 
It is only meant for demo purposes and in no way a recommended way to implement chat sessions in combination with Restate agents. 