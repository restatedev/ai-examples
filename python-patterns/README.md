# Patterns for building resilient LLM-based apps and agents with Restate

These patterns show how you can use Restate to harden LLM-based routing decisions and tool executions.

These small self-contained patterns can be mixed and matched to build more complex agents or workflows.

The patterns included here:
- [Chaining LLM calls](app/chaining.py): Build fault-tolerant processing pipelines where each step transforms the previous step's output.
- [Tool routing](app/routing_to_tool.py): Automatically route requests to tools based on LLM outputs.
- [Parallel tool execution](app/parallel_tools.py): Execute multiple tools in parallel with durable results that persist across failures.
- [Multi-agent routing](app/routing_to_agent.py): Route requests to specialized agents based on LLM outputs.
- [Remote agent routing](src/routing-to-remote-agent.ts): Deploy/scale agents separately and route requests with resilient communication.
- [Parallel agent processing](app/parallel_agents.py): Run multiple, specialized agents in parallel and aggregate their results.
- [Racing agents](app/racing_agents.py): Race multiple agents and return the result from whichever completes first successfully.
- [Orchestrator-worker pattern](app/orchestrator_workers.py): Break down complex tasks into specialized subtasks and execute them in parallel.
- [Evaluator-optimizer pattern](app/evaluator_optimizer.py): Generate → Evaluate → Improve loop until quality criteria are met.
- [Human-in-the-loop pattern](app/human_in_the_loop.py): Implement resilient human approval steps that suspend execution until feedback is received.
- [Chat sessions](app/chat.py): Long-lived, stateful chat sessions that maintain conversation state across multiple requests.

## Why Restate?

The benefits of using Restate here are:
- 🔁 **Automatic retries** of failed tasks: LLM API down, timeouts, long-running tasks, infrastructure failures, etc. Restate guarantees all tasks run to completion exactly once.
- ✅ **Recovery of previous progress**: After a failure, Restate recovers the progress the execution did before the crash. 
It persists routing decisions, tool execution outcomes, and deterministically replays them after failures, as opposed to executing them again. 
- 🧠 **Exactly-once execution** - Automatic deduplication of requests and tool executions via idempotency keys.
- 💾 **Persistent memory** - Maintain session state across infrastructure events.
The state can be queried from the outside. Stateful sessions are long-lived and can be resumed at any time.
- 🎮 **Task control** - Cancel tasks, query status, re-subscribe to ongoing tasks, and track progress across failures, time, and processes.


## Running the examples

1. Export your OpenAI API key as an environment variable:
    ```shell
    export OPENAI_API_KEY=your_openai_api_key
    ```
2. [Start the Restate Server](https://docs.restate.dev/develop/local_dev) in a separate shell:
    ```shell
    restate-server
    ```
3. Start the services:
    ```shell
    uv run .
    ```
4. Register the services (use `--force` if you already had another deployment registered at 9080): 
    ```shell
    restate -y deployments register localhost:9080 --force
    ```

### Chaining LLM calls
[<img src="https://raw.githubusercontent.com/restatedev/img/refs/heads/main/show-code.svg">](app/chaining.py)
[<img src="https://raw.githubusercontent.com/restatedev/img/refs/heads/main/read-guide.svg">](https://docs.restate.dev/ai/patterns/prompt-chaining)

Build fault-tolerant processing pipelines where each step transforms the previous step's output.

In the UI (`http://localhost:9070`), click on the `process` handler of the `CallChainingService` to open the playground and send a default request:

<img width="1200px" src="https://raw.githubusercontent.com/restatedev/ai-examples/refs/heads/main/doc/img/patterns/chaining_playground.png" alt="Chaining LLM calls - UI"/>

You see in the Invocations Tab of the UI how the LLM is called multiple times, and how the results are refined step by step:

<img width="1200px" src="https://raw.githubusercontent.com/restatedev/ai-examples/refs/heads/main/doc/img/patterns/chaining.png" alt="Chaining LLM calls - UI"/>

### Tool routing
[<img src="https://raw.githubusercontent.com/restatedev/img/refs/heads/main/show-code.svg">](app/routing_to_tool.py)
[<img src="https://raw.githubusercontent.com/restatedev/img/refs/heads/main/read-guide.svg">](https://docs.restate.dev/ai/patterns/tools)

Automatically route requests to tools based on LLM outputs. The agent keeps calling the LLM and executing tools until a final answer is returned.

In the UI (`http://localhost:9070`), click on the `route` handler of the `ToolRouter` service to open the playground and send a default request:

<img width="1200px" src="https://raw.githubusercontent.com/restatedev/ai-examples/refs/heads/main/doc/img/patterns/routing_local_tools_playground.png" alt="Dynamic routing LLM calls - UI"/>

In the UI, you can see how the LLM decides to forward the request to the technical support tools, and how the response is processed:

<img width="1200px" src="https://raw.githubusercontent.com/restatedev/ai-examples/refs/heads/main/doc/img/patterns/routing_local_tools.png" alt="Dynamic routing based on LLM output - UI"/>

### Parallel tool execution
[<img src="https://raw.githubusercontent.com/restatedev/img/refs/heads/main/show-code.svg">](app/parallel_tools.py)
[<img src="https://raw.githubusercontent.com/restatedev/img/refs/heads/main/read-guide.svg">](https://docs.restate.dev/ai/patterns/durable-webhooks)

Execute multiple tools in parallel with durable results that persist across failures.

In the UI (`http://localhost:9070`), click on the `run` handler of the `ParallelToolAgent` to open the playground and send a default request:

<img width="1200px" src="https://raw.githubusercontent.com/restatedev/ai-examples/refs/heads/main/doc/img/patterns/parallel_tools_playground.png" alt="Parallel tool calls - UI"/>

You see in the UI how the different tools are executed in parallel:

<img width="1200px" src="https://raw.githubusercontent.com/restatedev/ai-examples/refs/heads/main/doc/img/patterns/parallel_tools.png" alt="Parallel tool calls - UI"/>

Once all tools are done, the results are aggregated and returned to the client.

### Multi-agent routing
[<img src="https://raw.githubusercontent.com/restatedev/img/refs/heads/main/show-code.svg">](app/routing_to_agent.py)
[<img src="https://raw.githubusercontent.com/restatedev/img/refs/heads/main/read-guide.svg">](https://docs.restate.dev/ai/patterns/multi-agent)

Route requests to specialized agents based on LLM outputs. Routing decisions are persisted and can be retried.

In the UI (`http://localhost:9070`), click on the `answer` handler of the `AgentRouter` service to open the playground and send a default request:

<img width="1200px" src="https://raw.githubusercontent.com/restatedev/ai-examples/refs/heads/main/doc/img/patterns/routing_local_agent_playground.png" alt="Multi-agent routing - UI"/>

In the UI, you can see how the LLM decides to forward the request to the specialized support agents, and how the response is processed:

<img width="1200px" src="https://raw.githubusercontent.com/restatedev/ai-examples/refs/heads/main/doc/img/patterns/routing_local_agent.png" alt="Multi-agent routing - UI"/>

### Remote agent routing
[<img src="https://raw.githubusercontent.com/restatedev/img/refs/heads/main/show-code.svg">](app/routing_to_remote_agent.py)
[<img src="https://raw.githubusercontent.com/restatedev/img/refs/heads/main/read-guide.svg">](https://docs.restate.dev/ai/patterns/multi-agent)

Route requests to remote agents with resilient communication. 
Restate proxies requests to remote agents, persisting routing decisions and results. 
In case of failures, Restate retries failed executions.

In the UI (`http://localhost:9070`), click on the `answer` handler of the `RemoteAgentRouter` service to open the playground and send a default request:

<img width="1200px" src="https://raw.githubusercontent.com/restatedev/ai-examples/refs/heads/main/doc/img/patterns/routing_remote_agent_playground.png" alt="Multi-agent routing - UI"/>

In the UI, you can see how the LLM decides to forward the request to the specialized support agents, and how the nested call is also shown in the UI:

<img width="1200px" src="https://raw.githubusercontent.com/restatedev/ai-examples/refs/heads/main/doc/img/patterns/routing_remote_agent.png" alt="Multi-agent routing - UI"/>

### Parallel agent processing
[<img src="https://raw.githubusercontent.com/restatedev/img/refs/heads/main/show-code.svg">](app/parallel_agents.py)
[<img src="https://raw.githubusercontent.com/restatedev/img/refs/heads/main/read-guide.svg">](https://docs.restate.dev/ai/patterns/parallelization)

Run multiple, specialized agents in parallel and aggregate their results. If any agent fails, Restate retries only the failed agents while preserving completed results.

In the UI (`http://localhost:9070`), click on the `analyze` handler of the `ParallelAgentsService` to open the playground and send a default request:

<img width="1200px" src="https://raw.githubusercontent.com/restatedev/ai-examples/refs/heads/main/doc/img/patterns/parallel_agents_playground.png" alt="Parallel agents - UI"/>

You see in the UI how the different agents are executed in parallel:
<img width="1200px" src="https://raw.githubusercontent.com/restatedev/ai-examples/refs/heads/main/doc/img/patterns/parallel_agents.png" alt="Parallel agents - UI"/>

Once all agents are done, the results are aggregated and returned to the client.

### Racing agents
[<img src="https://raw.githubusercontent.com/restatedev/img/refs/heads/main/show-code.svg">](app/racing_agents.py)
[<img src="https://raw.githubusercontent.com/restatedev/img/refs/heads/main/read-guide.svg">](https://docs.restate.dev/ai/patterns/competitive-racing)

Execute multiple AI approaches or strategies simultaneously and return the result from whichever completes first successfully.

Restate turns Promises/Futures into durable, distributed constructs that persist across failures and process restarts.

In the UI (`http://localhost:9070`), click on the `run` handler of the `RacingAgent` service to open the playground and send a default request:

<img width="1200px" src="https://raw.githubusercontent.com/restatedev/ai-examples/refs/heads/typescript_patterns/doc/img/patterns/racing_playground.png" alt="Racing agents - UI"/>

You see in the UI how the different agents are executed in parallel and the first successful result is returned, while the other agents are cancelled:

<img width="1200px" src="https://raw.githubusercontent.com/restatedev/ai-examples/refs/heads/typescript_patterns/doc/img/patterns/racing.png" alt="Racing agents - UI"/>

### Human-in-the-loop pattern
[<img src="https://raw.githubusercontent.com/restatedev/img/refs/heads/main/show-code.svg">](app/human_in_the_loop.py)
[<img src="https://raw.githubusercontent.com/restatedev/img/refs/heads/main/read-guide.svg">](https://docs.restate.dev/ai/patterns/human-in-the-loop)

Implement resilient human approval steps that suspend execution until feedback is received. Durable promises survive crashes and can be recovered across process restarts.

In the UI (`http://localhost:9070`), click on the `moderate` handler of the `HumanInTheLoopService` to open the playground and send a default request:

<img width="1200px" src="https://raw.githubusercontent.com/restatedev/ai-examples/refs/heads/main/doc/img/patterns/human-in-the-loop-playground.png" alt="Human-in-the-loop pattern - UI"/>

Test this out by killing the service halfway through or restarting the Restate Server. You will notice that Restate will still be able to resolve the promise and invoke the handler again.

Then use the **curl command printed in the service logs** to provide your feedback.

You can see how the feedback gets incorporated in the Invocations tab in the Restate UI (`http://localhost:9070`):

<img width="1200px" src="https://raw.githubusercontent.com/restatedev/ai-examples/refs/heads/main/doc/img/patterns/human-in-the-loop.png" alt="Human-in-the-loop pattern - UI"/>

### Chat sessions
[<img src="https://raw.githubusercontent.com/restatedev/img/refs/heads/main/show-code.svg">](app/chat.py)
[<img src="https://raw.githubusercontent.com/restatedev/img/refs/heads/main/read-guide.svg">](https://docs.restate.dev/ai/patterns/sessions-and-chat)

Long-lived, stateful chat sessions that maintain conversation state across multiple requests. Sessions survive failures and can be resumed at any time.

In the UI (`http://localhost:9070`), click on the `message` handler of the `Chat` service to open the playground and send a default request:

<img width="1200px" src="https://raw.githubusercontent.com/restatedev/ai-examples/refs/heads/main/doc/img/patterns/chat-1.png" alt="Chat" width="900px"/>

You can then provide feedback on the response by sending new messages to the same session:

<img width="1200px" src="https://raw.githubusercontent.com/restatedev/ai-examples/refs/heads/main/doc/img/patterns/chat-2.png" alt="Chat" width="900px"/>

In the invocations tab, you can see how the memory was loaded and stored in Restate:
<img width="1200px" src="https://raw.githubusercontent.com/restatedev/ai-examples/refs/heads/main/doc/img/patterns/chat.png" alt="Chat - UI"/>

Go to the state tab of the UI to see the state of the chat session:

<img width="1200px" src="https://raw.githubusercontent.com/restatedev/ai-examples/refs/heads/main/doc/img/patterns/chat-state.png" alt="Chat" width="900px"/>


### Orchestrator-worker pattern
[<img src="https://raw.githubusercontent.com/restatedev/img/refs/heads/main/show-code.svg">](app/orchestrator_workers.py)

Break down complex tasks into specialized subtasks and execute them in parallel. If any worker fails, Restate retries only that worker while preserving other completed work.

In the UI (`http://localhost:9070`), click on the `process` handler of the `Orchestrator` to open the playground and send a default request:

<img width="1200px" src="https://raw.githubusercontent.com/restatedev/ai-examples/refs/heads/main/doc/img/patterns/orchestrator-playground.png" alt="Orchestrator LLM calls - UI"/>

In the UI, you can see how the LLM split the task in three parts and how each of the worker LLMs execute their tasks in parallel:

<img width="1200px" src="https://raw.githubusercontent.com/restatedev/ai-examples/refs/heads/main/doc/img/patterns/orchestrator.png" alt="Orchestrator-worker pattern - UI"/>

### Evaluator-optimizer pattern
[<img src="https://raw.githubusercontent.com/restatedev/img/refs/heads/main/show-code.svg">](app/evaluator_optimizer.py)

Generate → Evaluate → Improve loop until quality criteria are met. Restate persists each iteration, resuming from the last completed step on failure.

In the UI (`http://localhost:9070`), click on the `run` handler of the `EvaluatorOptimizer` to open the playground and send a default request:

<img width="1200px" src="https://raw.githubusercontent.com/restatedev/ai-examples/refs/heads/main/doc/img/patterns/evaluator-playground.png" alt="Evaluator-optimizer pattern - UI"/>

In the UI, you can see how the LLM generates a response, and how the evaluator LLM evaluates it and asks for improvements until the response is satisfactory:

<img width="1200px" src="https://raw.githubusercontent.com/restatedev/ai-examples/refs/heads/main/doc/img/patterns/evaluator.png" alt="Evaluator-optimizer pattern - UI"/>
