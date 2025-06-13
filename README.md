<!-- markdown-link-check-disable -->
[![Documentation](https://img.shields.io/badge/doc-reference-blue)](https://docs.restate.dev)
[![Discord](https://img.shields.io/discord/1128210118216007792?logo=discord)](https://discord.gg/skW3AZ6uGd)
[![Slack](https://img.shields.io/badge/Slack-4A154B?logo=slack&logoColor=fff)](https://join.slack.com/t/restatecommunity/shared_invite/zt-2v9gl005c-WBpr167o5XJZI1l7HWKImA)
[![Twitter](https://img.shields.io/twitter/follow/restatedev.svg?style=social&label=Follow)](https://x.com/intent/follow?screen_name=restatedev)
<!-- markdown-link-check-enable -->

# Restate: SDK-agnostic resilient agentic workflows 

Restate turns brittle agents into **resilient agents**.

Restate is Agent-SDK-agnostic and turns your agentic workflows into **reliable applications** that work consistently in production.

Restate has got your back: whether you start by adding resiliency to an existing agent SDK, or decide the agent SDK not flexible enough and implement everything from scratch while keeping your resiliency guarantees.


## Restate + Vercel AI SDK

**[<img src="https://skillicons.dev/icons?i=ts" width="24" height="24"> Minimal template](get-started/vercel-ai)**

For a more advanced example that can be deployed as a Next.js app on Vercel, check out this [Vercel AI SDK example](agents/vercel-ai-sdk/README.md).

## Restate + OpenAI Agent SDK
**[<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24"> Minimal template](get-started/openai-agents-python)**

For a more advanced example (including handoffs etc.), check out this [OpenAI Agent SDK example](agents/openai-agents-python/README.md).

## Why Restate?
[Restate](https://ai.restate.dev/) lets you easily build **reliable applications** that work consistently in production. 
Restate's capabilities and programming model work very well for implementing **agentic workflows**.
Move beyond fragile demos by giving your agents **innate resilience**—persistent memory, fault-tolerant tool/LLM calls, and robust handling of long-running tasks. Focus on your agent's intelligence, not the infrastructure complexity tax.

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

human in the loop

sdk-agnostic

Restate can also be used for other use cases, such as: 
[workflows](https://docs.restate.dev/use-cases/workflows),
[microservice orchestration](https://docs.restate.dev/use-cases/microservice-orchestration),
[async tasks](https://docs.restate.dev/use-cases/async-tasks), 
and [event processing](https://docs.restate.dev/use-cases/event-processing).
Or check out the [Restate examples repository](https://github.com/restatedev/examples).

This repository contains examples of how to use Restate for AI / Agent use cases.

## Full Example Catalog

1. [**Get started**](get-started): 
   - [<img src="https://skillicons.dev/icons?i=ts" width="24" height="24"> Restate + Vercel AI SDK](get-started/vercel-ai): A minimal example of how to use Restate with the Vercel AI SDK.
   - [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24"> Restate + OpenAI Agents SDK](get-started/openai-agents-python): A minimal example of how to use Restate with the OpenAI Agents SDK.
2. [**Agents**](agents): 
   - [<img src="https://skillicons.dev/icons?i=ts" width="24" height="24"> Restate + Vercel AI SDK](agents/vercel-ai-sdk): A more advanced example of how to use Restate with the Vercel AI SDK that can be deployed as a Next.js app on Vercel.
   - [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24"> Restate + OpenAI Agents SDK](agents/openai-agents-python): A more advanced example of how to use Restate with the OpenAI Agents SDK.
2. [**DIY patterns**](diy-patterns): Patterns for hardening custom LLM orchestration logic.
   - [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24"> Chaining LLM calls](diy-patterns#chaining-llm-calls)
   - [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24"> Parallelizing tool calls](diy-patterns#parallelizing-tool-calls)
   - [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24"> Dynamic routing based on LLM output](diy-patterns#dynamic-routing-based-on-llm-output)
   - [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24"> Orchestrator-worker](diy-patterns#orchestrator-worker-pattern)
   - [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24"> Evaluator-optimizer](diy-patterns#evaluator-optimizer-pattern)
   - [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24"> Human-in-the-loop](diy-patterns#human-in-the-loop-pattern)
3. [**MCP** <img src="https://skillicons.dev/icons?i=ts" width="24" height="24">](mcp): Using Restate for exposing tools and resilient orchestration of tool calls.
4. [**A2A** <img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24"> ](a2a): Implement Google's Agent-to-Agent protocol with Restate as resilient, scalable task orchestrator.
5. [**Advanced examples**](end-to-end-applications): 
   - [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24"> Customizable Restate agent loop](advanced/restate-native-agent)
   - [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24"> Interruptible agents](advanced/interruptible-agent): A customized agent with different operational modes to process new inputs: interrupting, incorporating, queueing.
   - [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24"> Insurance claims](advanced/insurance-claims): Filing insurance claims by parsing PDF receipts with LLMs.


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
- **vs. Heavy Workflow Engines:** Offers similar strong execution guarantees but with a lighter footprint, lower latency, simpler programming model, native serverless integration, and easier self-hosting/operational story—often a better fit for the potentially high-volume, interactive nature of agent applications.

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

**Disclaimer 3**: Some of the A2A examples in this repo are based on the examples included in the [Google A2A repo](https://github.com/google/A2A/tree/main).