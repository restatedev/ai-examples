# Tour of AI Agents with Restate - Python (no agent SDK)

A collection of examples showing how to build resilient AI agents with the [Restate Python SDK](https://docs.restate.dev/develop/python/overview) and [LiteLLM](https://docs.litellm.ai/) for model calls, without using an agent framework. You manage the agent loop yourself with full control over execution.

## Examples

| Pattern | Description | Docs | Code |
|---------|-------------|------|------|
| **Durable sessions** | Persistent, isolated agent sessions | [📖](https://docs.restate.dev/ai/patterns/sessions) | [chat_agent.py](app/chat_agent.py) |
| **Human approvals** | Human approval steps that suspend execution | [📖](https://docs.restate.dev/ai/patterns/human-in-the-loop) | [human_approval_agent.py](app/human_approval_agent.py) |
| **Human approvals with timeout** | Approvals with configurable timeout | [📖](https://docs.restate.dev/ai/patterns/human-in-the-loop) | [human_approval_agent_with_timeout.py](app/human_approval_agent_with_timeout.py) |
| **Multi-agent orchestration** | Route requests to specialized agents | [📖](https://docs.restate.dev/ai/patterns/multi-agent) | [multi_agent.py](app/multi_agent.py) |
| **Parallel tool calls** | Run multiple tools in parallel with recovery | [📖](https://docs.restate.dev/ai/patterns/parallelization) | [parallel_tools_agent.py](app/parallel_tools_agent.py) |
| **Workflow: Sequential pipeline** | Chain agents in multi-step pipelines | [📖](https://docs.restate.dev/ai/patterns/workflow-sequential) | [workflow_sequential.py](app/workflow_sequential.py) |
| **Workflow: Parallel agents** | Execute multiple agents in parallel | [📖](https://docs.restate.dev/ai/patterns/workflow-parallel) | [workflow_parallel.py](app/workflow_parallel.py) |
| **Workflow: Orchestrator-worker** | Break tasks into specialized subtasks | [📖](https://docs.restate.dev/ai/patterns/workflow-orchestrator) | [workflow_orchestrator.py](app/workflow_orchestrator.py) |
| **Workflow: Evaluator-optimizer** | Generate, evaluate, improve loop | [📖](https://docs.restate.dev/ai/patterns/workflow-evaluator) | [workflow_evaluator_optimizer.py](app/workflow_evaluator_optimizer.py) |
| **Remote agents** | Deploy/scale agents separately with resilient RPC | [📖](https://docs.restate.dev/ai/patterns/remote-agents) | [remote_agents.py](app/remote_agents.py) |
| **Competitive racing** | Run parallel agents, use the fastest response | [📖](https://docs.restate.dev/ai/patterns/competitive-racing) | [racing_agents.py](app/racing_agents.py) |

## Run the examples

1. Export your OpenAI API key as an environment variable:
    ```shell
    export OPENAI_API_KEY=your_openai_api_key
    ```
2. [Start the Restate Server](https://docs.restate.dev/installation) in a separate shell:
    ```shell
    restate-server
    ```
3. Start the agent you want to run:
    ```shell
    uv run app/chat_agent.py
    ```
4. Register the services (use `--force` if you already had another deployment registered at 9080):
    ```shell
    restate -y deployments register localhost:9080 --force
    ```
5. In the UI, click on the handler to go to the playground, and send a request.
