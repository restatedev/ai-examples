# Tour of AI Agents with Restate - Google ADK

Learn how to implement resilient agents with durable execution, human-in-the-loop, multi-agent communication, and parallel execution.

[Learn more in the docs](https://docs.restate.dev/tour/google-adk)

## Run the examples

Export your OpenAI API key:
```bash
export OPENAI_API_KEY=your-key
```

Or run an agent:
```bash
uv run app/durable_agent.py
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
