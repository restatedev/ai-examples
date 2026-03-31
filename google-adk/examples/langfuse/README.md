# Restate + Google ADK + LangFuse example

This example shows how to get full observability over your agentic workflows by combining [Restate](https://restate.dev/) with [LangFuse](https://langfuse.com/).

It implements an insurance claim processor that mixes LLM agent steps (document parsing, claim analysis) with regular workflow steps (currency conversion, reimbursement).
Restate orchestrates the workflow durably and exports OpenTelemetry traces. A Restate tracing processor attaches the Google ADK spans to the Restate trace, so everything shows up as a single unified trace in LangFuse: LLM calls with their prompts, model config, and outputs alongside the durable workflow steps.

## Running the example
[See `agent.py`](agent.py)

**Prerequisites**:

- [LangFuse account and API key](https://langfuse.com/)
- [OpenAI API key](https://platform.openai.com/api-keys)

**Install Restate** via brew or [other installation methods](https://docs.restate.dev/installation#install-restate-server-&-cli):

```bash
brew install restatedev/tap/restate-server restatedev/tap/restate
```

**Download the example**:

```bash
restate example python-google-adk-examples
cd python-google-adk-examples/langfuse
```

**Add your API keys** to an `.env` file:

```bash
echo 'LANGFUSE_PUBLIC_KEY=pk-lf-...' > .env                                                                                                                                   
echo 'LANGFUSE_SECRET_KEY=sk-lf-...' >> .env              
echo 'LANGFUSE_HOST=https://cloud.langfuse.com' >> .env 
echo 'GOOGLE_API_KEY=sk-proj-...' >> .env 
```

**Start the agent service**:

```bash
uv run --env-file .env . 
```

**Start Restate**:

```bash
# Export LangFuse API keys
source .env 
export RESTATE_TRACING_HEADERS__AUTHORIZATION="Basic $(echo -n "${LANGFUSE_PUBLIC_KEY}:${LANGFUSE_SECRET_KEY}" | base64)"

restate-server --tracing-endpoint otlp+https://cloud.langfuse.com/api/public/otel/v1/traces
```

Restate exports OTEL traces. By setting the tracing endpoint and headers, we can export traces to LangFuse.

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

You can now **inspect the trace in LangFuse**.
