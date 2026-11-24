# Durable document search with Loom

Search a team runbook collection with [Loom](https://github.com/ClickHouse/loom)
before passing excerpts and their source URIs to an agent. The Restate handler
runs the search as a named `ctx.run_typed` step. Restate retries a transient
failure and reuses a completed result during replay. A new invocation searches
again. The example uses keyword search with reranking disabled.

The worker reads its Loom viewer token from the environment. The handler uses
one shared token and namespace for all callers. Keep it behind private or
authenticated Restate ingress, and give access only to callers who may see the
namespace. Restate persists the request and excerpts in its journal, so grant
journal access to the same audience.

## Run the example

1. Start a local [Restate server](https://docs.restate.dev/installation). Prepare
   a searchable Loom namespace with at least one runbook and a viewer token for
   that namespace. Use HTTPS for a remote Loom deployment.
2. From this directory, set `LOOM_BASE_URL`, `LOOM_ORG`, `LOOM_NAMESPACE`, and
   `LOOM_TOKEN` in the worker environment and start the service.

   ```sh
   uv run .
   ```

3. Register the service and call the search handler.

   ```sh
   restate -y deployments register http://127.0.0.1:9080
   curl http://127.0.0.1:8080/LoomKnowledge/search \
     --json '{"query":"roll back a deployment"}'
   ```

4. Open the completed invocation in the Restate UI to see the `Search runbooks`
   step. The handler returns up to three excerpts, each with its `source_uri`.
   A query with no matching runbook returns an empty list.
