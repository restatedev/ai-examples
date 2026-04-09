# Restate + OpenAI Agents SDK + Arize Phoenix example

This example shows how to get full observability over your agentic workflows by combining [Restate](https://restate.dev/) with [Arize Phoenix](https://phoenix.arize.com/).

It implements an insurance claim processor that mixes LLM agent steps (document parsing, claim analysis) with regular workflow steps (currency conversion, reimbursement).
Restate orchestrates the workflow durably and exports OpenTelemetry traces. A Restate tracing processor attaches the OpenAI Agents SDK spans to the Restate trace, so everything shows up as a single unified trace in Arize Phoenix: LLM calls with their prompts, model config, and outputs alongside the durable workflow steps.

## Running the example
[See `agent.py`](agent.py)

**Prerequisites**:

- [Arize Phoenix](https://docs.arize.com/phoenix) with a [Phoenix Cloud account and API key](https://app.phoenix.arize.com/)
- [OpenAI API key](https://platform.openai.com/api-keys)

**Install Restate** via brew or [other installation methods](https://docs.restate.dev/installation#install-restate-server-&-cli):

```bash
brew install restatedev/tap/restate-server restatedev/tap/restate
```

**Download the example**:

```bash
restate example python-openai-agents-examples
cd python-openai-agents-examples/arize_phoenix
```

Set the environment variables:

```bash
echo 'OPENAI_API_KEY=sk-proj-...' > .env
echo 'PHOENIX_COLLECTOR_ENDPOINT=https://app.phoenix.arize.com/s/your-account-name' >> .env
echo 'PHOENIX_API_KEY=...' >> .env
echo 'PHOENIX_PROJECT_NAME=...' >> .env
```

**Start the agent service**:

```bash
uv run --env-file .env . 
```

Start the Restate Server:

```bash
source .env
export RESTATE_TRACING_HEADERS__AUTHORIZATION="Bearer ${PHOENIX_API_KEY}"

restate-server --tracing-endpoint otlp+https://app.phoenix.arize.com/s/your-account-name/v1/traces
```

Replace your-account-name with the name of your Phoenix account.

Restate exports OTEL traces. By setting the tracing endpoint, we can export traces to Arize Phoenix.

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

You can now **inspect the trace in Arize Phoenix**.
