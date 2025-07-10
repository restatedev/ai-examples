<!-- markdown-link-check-disable -->
[![Documentation](https://img.shields.io/badge/doc-reference-blue)](https://docs.restate.dev)
[![Discord](https://img.shields.io/discord/1128210118216007792?logo=discord)](https://discord.gg/skW3AZ6uGd)
[![Slack](https://img.shields.io/badge/Slack-4A154B?logo=slack&logoColor=fff)](https://join.slack.com/t/restatecommunity/shared_invite/zt-2v9gl005c-WBpr167o5XJZI1l7HWKImA)
[![Twitter](https://img.shields.io/twitter/follow/restatedev.svg?style=social&label=Follow)](https://x.com/intent/follow?screen_name=restatedev)
<!-- markdown-link-check-enable -->

# Examples for AI workflows and Durable Agents

This repo contains a set of runnable examples of AI workflows and agents, using  **Durable Execution and Orchestration** via [Restate](https://restate.dev/) ([Github](https://restatedev/restate))

The goal is to show how you can easily add production-grade _resilience_, _state persistence_, _retries_, _suspend/resume_, _human-in-the-loop_, and _observability_ to agentic workflows. So you can ship agents that stay alive and consistent without sprinkling retry-code everywhere and without building heavyweight infra yourself.

The Restate approach works **independent of specific SDKs** but **integrates easily with popular SDKs**, like the [Vercel AI SDK](https://ai-sdk.dev/) or the [OpenAI Agent SDK](https://openai.github.io/openai-agents-python/). You can also use without and Agent SDK _(roll your own loop)_ or for more traditional workflows.

📄 A gentle intro is in [the blog post "Durable Agents - Fault Tolerance across Frameworks and without Handcuffs"](https://restate.dev/blog/durable-ai-loops-fault-tolerance-across-frameworks-and-without-handcuffs/)

### Restate + Vercel AI SDK

- **[<img src="https://skillicons.dev/icons?i=ts" width="24" height="24"> Template](vercel-ai/template)**
- [More examples (including Next.js, multi-agent, etc.)](vercel-ai/examples).

### Restate + OpenAI Agent SDK

- **[<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24"> Template](openai-agents/template)**
- [More examples (including handoffs, memory, etc.)](openai-agents/examples).

### Roll your own Loop? AI-enriched workflows?

Restate is a flexible general-purpose runtime for what we call _innately resilient application_. It is not limited to agentic workflow use cases and is being used for a variety of other use cases as well, including financial transactions or order processing. These examples show how to build agents directly on Restate's durable execution and state management:

- [Standalone Agent](advanced/restate-native-agent/)


## Use Cases

| Use Case                           | What it solves                                                                              |
| ---------------------------------- | ------------------------------------------------------------------------------------------- |
| **Durable Execution**              | Crash-safe LLM/tool calls & idempotent retries—agents resume at the last successful step.   |
| **Journal Observability**          | Auto-captured journal of every step, retry, and message for easy debugging and auditing.    |
| **Human-in-the-loop & long waits** | Suspend while waiting for user approval or slow jobs; pay for compute, not wall-clock time. |
| **Stateful sessions / memory**     | Virtual Objects keep multi-turn conversations and other state isolated and consistent.      |
| **Multi-agent orchestration**      | Reliable RPC, queuing, and scheduling between agents running in separate processes.         |


<p style="text-align: center;">
  <img src="vercel-ai/examples/doc/img/multi_agent_complete.png" alt="OpenAI Agent SDK invocation UI" width="600px"/><br/>
  Restate UI showing an ongoing agent execution
</p>


## Full Example Catalog

1. [**Restate + Vercel AI**](vercel-ai): 
   - [<img src="https://skillicons.dev/icons?i=ts" width="24" height="24"> Template](vercel-ai/template): A minimal example of how to use Restate with the Vercel AI SDK.
   - [<img src="https://skillicons.dev/icons?i=ts" width="24" height="24"> Examples](vercel-ai/examples): A more advanced example of how to use Restate with the Vercel AI SDK that can be deployed as a Next.js app on Vercel.
2. [**Restate + OpenAI Agents Python SDK**](openai-agents): 
   - [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24"> Template](openai-agents/template): A minimal example of how to use Restate with the OpenAI Agents SDK.
   - [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24"> Examples](openai-agents/examples): A more advanced example of how to use Restate with the OpenAI Agents SDK.
2. [**Patterns**](patterns) for hardening custom LLM orchestration logic.
   - [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24"> Chaining LLM calls](patterns#chaining-llm-calls)
   - [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24"> Parallelizing tool calls](patterns#parallelizing-tool-calls)
   - [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24"> Dynamic routing based on LLM output](patterns#dynamic-routing-based-on-llm-output)
   - [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24"> Orchestrator-worker](patterns#orchestrator-worker-pattern)
   - [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24"> Evaluator-optimizer](patterns#evaluator-optimizer-pattern)
   - [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24"> Human-in-the-loop](patterns#human-in-the-loop-pattern)
3. [**MCP** <img src="https://skillicons.dev/icons?i=ts" width="24" height="24">](mcp): Using Restate for exposing tools and resilient orchestration of tool calls.
4. [**A2A** <img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24"> ](a2a): Implement Google's Agent-to-Agent protocol with Restate as resilient, scalable task orchestrator.
5. [**Advanced examples**](end-to-end-applications): 
   - [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24"> Restate-native agent](advanced/restate-native-agent/README.md): A fully customizable agent implemented with Restate without an Agent SDK. 
   - [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24"> Interruptible agents](advanced/interruptible-agent/README.md): A customized agent with different operational modes to process new inputs: interrupting, incorporating, queueing.
   - [<img src="https://skillicons.dev/icons?i=python&theme=light" width="24" height="24"> Insurance claims](advanced/insurance-claims/README.md): Filing insurance claims by parsing PDF receipts with LLMs.


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
- [Documentation](https://docs.restate.dev/)
- [Quickstart](https://docs.restate.dev/get_started/quickstart)
- [Tour of Restate: a tutorial including the most important features](https://docs.restate.dev/get_started/tour)
- [Examples on workflows, microservice orchestration, async tasks, event processing](https://github.com/restatedev/examples)
- [Restate Cloud](https://restate.dev/cloud/)
- [Discord](https://discord.gg/skW3AZ6uGd) / [Slack](https://join.slack.com/t/restatecommunity/shared_invite/zt-2v9gl005c-WBpr167o5XJZI1l7HWKImA)

## Acknowledgements

- The implementations of the Restate-native agent in this repo are heavily inspired by the [OpenAI Agents SDK](https://github.com/openai/openai-agents-python). We therefore want to give credit to the developers of this SDK for the great work they have done. This repo builds further on their work to make it benefit from Restate's programming model and capabilities.

- The DIY patterns are largely based on Anthropic's [agents cookbook](https://github.com/anthropics/anthropic-cookbook/tree/main/patterns/agents).

- Some of the A2A examples in this repo are based on the examples included in the [Google A2A repo](https://github.com/google/A2A/tree/main).
