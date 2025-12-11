# Python Hello World

Python hello world project to get started.

Inside this repo, make a restate.toml file with the following content:

```toml
tracing-endpoint="https://cloud.langfuse.com/api/public/otel/v1/traces"

[tracing-headers]
authorization="Authorization=Basic your-key"
```

Then start the Restate server with:

```shell
restate-server --config-file restate.toml
```

Start the app:

```shell
uv run . 
```

Register the service:

```shell
restate -y deployments register localhost:9080
```

Call the agent:

```shell
curl localhost:8080/Agent/run --json '"What is the weather in Detroit?"'
```