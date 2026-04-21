# Abort & Regenerate

Interruptions are messages sent to an agent while it is already working. For a coding agent, this is essential: you notice the agent going off in the wrong direction, and you want to add missing context to get it back on track without waiting for the current task to finish.

Restate lets us implement interruptions with **cancellation signals**. Cancelling a running invocation causes it to terminally fail and raise an error at the next durable step, while still letting the handler run further durable actions such as cleanup and notifying the agent orchestrator. Cancellation automatically propagates through sub-invocations, giving you something similar to stack unwinding with exceptions — just distributed.

## How it works

Two services:

- **`CodingAgent`** — a Virtual Object, one per agent session. It holds the conversation history and the invocation ID of any running task.
- **`CodingTask`** — a long-running Service that performs multiple LLM steps (plan → draft → polish) in sequence.

The agent's `message` handler loads the conversation state, cancels any ongoing task (adding a note to the history), sends the new task, and persists the returned invocation ID. Inside `CodingTask.run_task`, the cancellation surfaces as a `TerminalError` at the next Restate await (the next `ctx.run_typed` LLM call). The task catches it, notifies the orchestrator, and re-raises so Restate records the invocation as cancelled.

[See `agent.py`](agent.py).

## Running the example

**Prerequisites:**

- [OpenAI API key](https://platform.openai.com/api-keys)

**Install Restate** via brew or [other installation methods](https://docs.restate.dev/installation#install-restate-server-&-cli):

```bash
brew install restatedev/tap/restate-server restatedev/tap/restate
```

**Add your API key** to an `.env` file:

```bash
echo 'OPENAI_API_KEY=sk-proj-...' > .env
```

**Start the agent service:**

```bash
uv run --env-file .env .
```

**Start Restate** (in another shell):

```bash
restate-server
```

**Register the services:**

```bash
restate -y deployments register localhost:9080 --force
```

## Sending messages

**Happy path** — one message, full plan/draft/polish output:

```bash
curl localhost:8080/CodingAgent/alice/message \
  --json '{"content":"Write me a small todo CLI in Python."}'

# Wait a few seconds, then:
curl localhost:8080/CodingAgent/alice/get_history
```

**Interruption path** — fire a first message, then interrupt before it finishes:

```bash
# Fire-and-forget the first message
curl localhost:8080/CodingAgent/bobb/message/send \
  --json '{"content":"Build a Flask app with user auth."}'

# Immediately interrupt with new context
curl localhost:8080/CodingAgent/bobb/message \
  --json '{"content":"Actually, use FastAPI instead of Flask."}'

curl localhost:8080/CodingAgent/bobb/get_history
```

Open the Restate UI at `http://localhost:9070` to inspect the invocations — the first `CodingTask.run_task` shows status `cancelled`, and the second `completed`.
