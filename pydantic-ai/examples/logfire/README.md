# Restate + Pydantic AI + LogFire example

This example shows how to get full observability over your agentic workflows by combining [Restate](https://restate.dev/) with Pydantic AI and [Pydantic LogFire](https://pydantic.dev/logfire).

It implements an insurance claim processor that mixes LLM agent steps (document parsing, claim analysis) with regular workflow steps (currency conversion, reimbursement).
Restate orchestrates the workflow durably and exports OpenTelemetry traces. A Restate tracing processor attaches the Pydantic AI spans to the Restate trace, so everything shows up as a single unified trace in LogFire: LLM calls with their prompts, model config, and outputs alongside the durable workflow steps.

## Running the example
[See `agent.py`](agent.py)

**Prerequisites**:

- [Pydantic LogFire account and write key](https://pydantic.dev/logfire)
- [OpenAI API key](https://platform.openai.com/api-keys)

**Install Restate** via brew or [other installation methods](https://docs.restate.dev/installation#install-restate-server-&-cli):

```bash
brew install restatedev/tap/restate-server restatedev/tap/restate
```

**Download the example**:

```bash
restate example python-pydantic-ai-examples
cd python-pydantic-ai-examples/logfire
```

**Add your API keys** to an `.env` file:

```bash
echo 'LOGFIRE_WRITE_TOKEN=your-write-token' >> .env
echo 'OPENAI_API_KEY=sk-proj-...' >> .env 
```

**Start the agent service**:

```bash
uv run --env-file .env . 
```

**Start Restate**:

```bash
# Export LogFire write token (=! API key)
source .env 
export RESTATE_TRACING_HEADERS__AUTHORIZATION="Bearer $LOGFIRE_WRITE_TOKEN"

restate-server --tracing-endpoint otlp+https://logfire-eu.pydantic.dev/v1/traces
```

Restate exports OTEL traces. By setting the tracing endpoint and headers, we can export traces to LogFire.

Now **register the service**, so Restate knows where it is running:

```bash
restate deployments add localhost:9080
```

**Send a request**:

```bash
curl localhost:8080/InsuranceClaimAgent/run \
  --json '{"text": "Customer ID: cus_123 - Hospital bill for broken leg treatment at General Hospital for 3000 euro on 24/04/26"}'
```

Send the request to Restate (`localhost:8080`) which persists it and then forwards it to the agent.

You can now **inspect the trace in LogFire**.