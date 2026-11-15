# Resilient A2A Agents with Restate

This example exposes agents over A2A 1.0 JSON-RPC using `a2a-sdk` 1.x and
[Restate](https://restate.dev/) for durable execution. The integration is still
work in progress; it is not a complete implementation of every A2A operation.

Each task runs inside a Restate virtual object. Calls, timers, state and completed
`ctx.run_typed` steps are journaled. After a Python worker restarts, Restate
replays the invocation and reuses completed step results.

## What is supported

- `SendMessage`, including `configuration.returnImmediately`.
- `GetTask`, with A2A 1.0 history semantics: omitted returns available history,
  zero omits history, and a positive value returns the last messages.
- `CancelTask`, including cancellation during an active invocation.
- Multi-turn tasks that pause in `TASK_STATE_INPUT_REQUIRED`.
- A discoverable Agent Card at `/.well-known/agent-card.json`.
- ProtoJSON messages and errors consumed by the official Python SDK 1.x client.

Streaming, push notifications, extended cards and task listing are not implemented.
The card advertises streaming and push notifications as disabled; unsupported
operations return A2A errors.

Protobuf values are converted to ProtoJSON before crossing Restate state or
journal boundaries. `AgentInvokeResult.parts` consequently contains ProtoJSON
parts such as `{"text": "hello"}`. A2A 0.3 `kind` discriminators, lowercase roles
and slash-separated method names are not used by this example.

## Prerequisites

- Python 3.12 or newer and [uv](https://docs.astral.sh/uv/).
- A local Restate server. The recovery tests were exercised with Restate 1.8.1.
- For the ADK agents, a Google API key in `GOOGLE_API_KEY` or `GEMINI_API_KEY`, or
  configured Vertex AI credentials. The deterministic recovery tests need no key.

Install the locked dependencies from this directory:

```sh
uv sync --locked
```

Start Restate, using a fresh data directory for this 1.x example:

```sh
restate-server --base-dir ./restate-data
```

## Weather agent

Run the worker:

```sh
uv run python -m app.weather
```

The worker listens on port 9080. Register its Restate endpoint:

```sh
restate deployments register http://localhost:9080/restate/v1 --yes
```

Discover the card:

```sh
curl -s http://localhost:9080/.well-known/agent-card.json
```

Call the JSON-RPC URL advertised in `supportedInterfaces`:

```sh
curl -s http://localhost:8080/WeatherAgentA2AServer/process_request \
  -H 'Content-Type: application/json' \
  -H 'A2A-Version: 1.0' \
  --data '{
    "jsonrpc": "2.0",
    "id": "weather-request-1",
    "method": "SendMessage",
    "params": {
      "message": {
        "messageId": "weather-message-1",
        "role": "ROLE_USER",
        "parts": [{"text": "What is the weather in Detroit?"}]
      }
    }
  }'
```

The task is at `result.task`; its state uses names such as
`TASK_STATE_COMPLETED`. The first request omits `taskId`. For follow-up messages,
use the returned task's `id` and `contextId`, with a new `messageId`.

## Reimbursement agent

```sh
uv run python -m app.reimbursement
restate deployments register http://localhost:9081/restate/v1 --yes
```

Discover `http://localhost:9081/.well-known/agent-card.json` and use the same
`SendMessage` shape at the advertised JSON-RPC URL. The agent requests missing
information and uses a Restate awakeable for human approval. Its logs print the
approval callback URL.

Retrieve or cancel a task using its returned ID:

```sh
curl -s http://localhost:8080/ReimbursementAgentA2AServer/process_request \
  -H 'Content-Type: application/json' -H 'A2A-Version: 1.0' \
  --data '{"jsonrpc":"2.0","id":"get-1","method":"GetTask","params":{"id":"TASK_ID","historyLength":10}}'

curl -s http://localhost:8080/ReimbursementAgentA2AServer/process_request \
  -H 'Content-Type: application/json' -H 'A2A-Version: 1.0' \
  --data '{"jsonrpc":"2.0","id":"cancel-1","method":"CancelTask","params":{"id":"TASK_ID"}}'
```

## Reproduce worker recovery without an LLM

Stop any existing local Restate server and workers on ports 8080, 9070, 9071,
5122 and 19080. The test suite starts its own server with a temporary data
store, registers a deterministic worker and cleans up its processes.

```sh
RESTATE_SERVER_BIN=/absolute/path/to/restate-server \
  uv run python -m unittest discover -s tests -v
```

Set `RESTATE_TEST_EVIDENCE=/path/to/output` to retain worker/server logs and the
step event ledger. No API keys or external agent services are used.

The tests verify:

1. An official SDK 1.x client can send and fetch tasks, and retrying a message
   with a different JSON-RPC correlation ID reuses the result.
2. After the first step's journal result is acknowledged, killing the worker
   with `SIGKILL` and restarting it allows the durable timer and second step to
   complete. The saved first step executes once in the observed run, and the
   second step's PID belongs to the replacement worker.
3. An approval wait survives the same worker kill and resumes after resolving
   the original awakeable.
4. The real ADK runner, Restate plugin and session service replay a saved model
   response after a worker kill. The model is a deterministic local `BaseLlm`;
   its response-generation code executes once in the observed run.
5. Multi-turn history preserves user/agent message order; cancellation and
   terminal errors produce persistent terminal task states. An agent's business
   conflict is a failure, not a cancellation.
6. Nonblocking follow-ups include the accepted message and can be retried after
   completion without executing the turn again.
7. Invalid requests and unsupported methods return the corresponding A2A errors;
   invalid JSON-RPC envelopes are rejected without retrying the invocation.

These checks exercise a real local Restate server and HTTP transport. They do
not establish successful Google/LLM execution, recovery from loss of the Restate
data store, or full A2A TCK conformance.

## Durability and upgrade boundaries

- Put nondeterministic work, LLM calls and external side effects inside durable
  steps or durable service calls. Code outside those boundaries executes again
  during replay.
- An external write can succeed before its result is journaled. That crash
  window still requires downstream idempotency; these tests do not demonstrate
  exactly-once execution of arbitrary external effects.
- This example deduplicates task invocations by `messageId` within a task object,
  for Restate's configured idempotency retention. Initial task IDs are derived
  deterministically from the agent service name and message ID. Reuse a message
  ID only for retries of the same message. JSON-RPC `id` is only correlation.
- The example has no authentication or tenant isolation. Add these at the
  application boundary before exposing it beyond a local development machine.
- The wire format, task state and journal command sequence changed from the 0.3
  example. Existing tasks/journals are not migrated. Drain the old deployment
  and use a separate endpoint/service namespace or a fresh local store; do not
  overwrite an in-flight 0.3 deployment with `--force`.
