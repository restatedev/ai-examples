# Tour of AI Agents with Restate - LangChain

A collection of examples showing how to build resilient AI agents with [LangChain](https://docs.langchain.com/oss/python/langchain/agents) and [Restate](https://restate.dev/).

## Examples

| Pattern | Description | Code |
|---------|-------------|------|
| **Durable sessions** | Persistent, isolated agent sessions | [chat_agent.py](app/chat_agent.py) |
| **Human approvals** | Human approval steps that suspend execution | [human_approval_agent.py](app/human_approval_agent.py) |
| **Human approvals with timeout** | Approvals with configurable timeout | [human_approval_agent_with_timeout.py](app/human_approval_agent_with_timeout.py) |
| **Multi-agent orchestration** | Route requests to specialized agents | [multi_agent.py](app/multi_agent.py) |
| **Parallel tool calls** | Run multiple tools in parallel with recovery | [parallel_tools_agent.py](app/parallel_tools_agent.py) |
| **Workflow: Sequential pipeline** | Chain agents in multi-step pipelines | [workflow_sequential.py](app/workflow_sequential.py) |
| **Workflow: Parallel agents** | Execute multiple agents in parallel | [workflow_parallel.py](app/workflow_parallel.py) |
| **Workflow: Orchestrator-worker** | Break tasks into specialized subtasks | [workflow_orchestrator.py](app/workflow_orchestrator.py) |
| **Workflow: Evaluator-optimizer** | Generate, evaluate, improve loop | [workflow_evaluator_optimizer.py](app/workflow_evaluator_optimizer.py) |
| **Workflows as tools** | Complex tool logic as separate durable services | [sub_workflow_agent.py](app/sub_workflow_agent.py) |
| **Remote agents** | Deploy/scale agents separately with resilient RPC | [remote_agents.py](app/remote_agents.py) |
| **Error handling** | Retries and error handling for agents | [error_handling.py](app/error_handling.py) |

## Run the examples

Export your OpenAI API key:
```bash
export OPENAI_API_KEY=your-key
```

Run an agent:
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

Invoke services via the UI (`http://localhost:8080/`).

## How the Restate-LangChain integration works

Pass `RestateMiddleware()` to `create_agent`:

```python
from langchain.agents import create_agent
from restate.ext.langchain import RestateMiddleware

agent = create_agent(model=..., tools=[...], middleware=[RestateMiddleware()])
```

- Every LLM call is journaled via `awrap_model_call`.
- Parallel tool calls are serialized by a turnstile keyed on `tool_call_id` so any `ctx.run_typed` calls inside tool bodies produce a deterministic journal order across replays.

Tool side effects are NOT auto-journaled — wrap them yourself with `restate_context().run_typed("name", ...)` inside the tool body for the steps you want to be durable.
