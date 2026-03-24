# Tour of AI Agents with Restate - OpenAI Agents SDK

A collection of examples showing how to build resilient AI agents with the [OpenAI Agents SDK](https://openai.github.io/openai-agents-python/) and [Restate](https://restate.dev/).

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
| **Workflows as tools** | Complex tool logic as separate durable services | [📖](https://docs.restate.dev/ai/patterns/tools) | [sub_workflow_agent.py](app/sub_workflow_agent.py) |
| **Remote agents** | Deploy/scale agents separately with resilient RPC | [📖](https://docs.restate.dev/ai/patterns/remote-agents) | [remote_agents.py](app/remote_agents.py) |
| **Error handling** | Retries and error handling for agents | [📖](https://docs.restate.dev/ai/patterns/error-handling) | [error_handling.py](app/error_handling.py) |

## Run the examples

Export your OpenAI API key:
```bash
export OPENAI_API_KEY=your-key
```

Or run an agent:
```bash
uv run app/chat_agent.py
```

Start Restate:
```bash
docker run --name restate_dev --rm \
  -p 8080:8080 -p 9070:9070 -p 9071:9071 \
  --add-host=host.docker.internal:host-gateway \
  docker.restate.dev/restatedev/restate:latest
```

Register the deployment:
```bash
curl localhost:9070/deployments --json '{"uri": "http://host.docker.internal:9080"}'
```

Invoke the service via the UI (`http://localhost:8080/`). Click on the agent handler you want to call and use the playground to send a request.
