# Interrupt & Regenerate

Interruptions are messages sent to an agent while it is already working. For a coding agent, this is essential: you notice the agent going off in the wrong direction, and you want to add missing context to get it back on track without waiting for the current task to finish.

Restate lets us implement interruptions with **cancellation signals**. Cancelling a running invocation causes it to terminally fail and raise an error at the next durable step, while still letting the handler run further durable actions such as cleanup and notifying the agent orchestrator. Cancellation automatically propagates through sub-invocations, giving you something similar to stack unwinding with exceptions — just distributed.

## How it works

Two services:

- **`CodingAgent`** — a Virtual Object, one per agent session. It holds the conversation history and the invocation ID of any running task.
- **`CodingTask`** — a long-running Service that performs multiple LLM steps (plan → draft → polish) in sequence.

The agent's `message` handler loads the conversation state, cancels any ongoing task (adding a note to the history), sends the new task, and persists the returned invocation ID. Inside `CodingTask.runTask`, the cancellation surfaces as a `CancelledError` at the next Restate await (the next `ctx.run` LLM call). The task catches it, notifies the orchestrator, and re-raises so Restate records the invocation as cancelled.

[See `src/agent.ts`](src/agent.ts).

## Running the example

**Prerequisites:** [OpenAI API key](https://platform.openai.com/api-keys)

**Install Restate** via brew or [other installation methods](https://docs.restate.dev/installation#install-restate-server-&-cli):

```bash
npx @restatedev/restate-server
```

**Install dependencies:**

```bash
npm install
```

**Start the agent service** with your API key:

```bash
OPENAI_API_KEY=sk-proj-... npm run dev
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
  --json '{"content":"Write me a small todo CLI in TypeScript."}'

# Wait a few seconds, then:
curl localhost:8080/CodingAgent/alice/getHistory
```

**Interruption path** — fire a first message, then interrupt before it finishes:

```bash
# Fire-and-forget the first message
curl localhost:8080/CodingAgent/bob/message/send \
  --json '{"content":"Build a Fastify app with user auth."}'

# Immediately interrupt with new context
curl localhost:8080/CodingAgent/bob/message \
  --json '{"content":"Actually, use Hono instead of Fastify."}'

curl localhost:8080/CodingAgent/bob/getHistory
```

Open the Restate UI at `http://localhost:9070` to inspect the invocations — the first `CodingTask.runTask` shows status `cancelled`, and the second `completed`.
