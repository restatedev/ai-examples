# Patterns for building resilient LLM-based apps and agents with Restate

These patterns show how you can use Restate to harden LLM-based routing decisions and tool executions.

They do not implement end-to-end agents, but serve as small self-contained patterns that can be mixed and matched to build more complex workflows.

The patterns included here:
- [Chaining LLM calls](chaining/service.py): Refine the results by calling the LLM iteratively with its own output.
- [Parallelizing tool calls](parallelization/service.py): Call multiple tools in parallel and wait for their results in a durable way. Tool calls are retried if they fail, and the results are persisted.
- [Dynamic routing based on LLM output](routing/service.py): Route the execution to different tools based on the LLM's output. Routing decisions are persisted and can be retried.
- [Orchestrator-worker pattern](orchestrator_workers/service.py): A resilient orchestration workflow in which a central LLM dynamically breaks down tasks, delegates them to worker LLMs, and analyzes their results.
- [Evaluator-optimizer pattern](evaluator_optimizer/service.py): Let the LLM generate a response, and ask another LLM to evaluate the response, and let them iterate on it.
- [Human-in-the-loop pattern](human_in_the_loop/service.py): An LLM generates a response, and then a human can review and approve the response before the LLM continues with the next step.

A part of these patterns are based on Anthropic's [agents cookbook](https://github.com/anthropics/anthropic-cookbook/tree/main/patterns/agents).

## Why Restate?

The benefits of using Restate here are:
- 🔁 **Automatic retries** of failed tasks: LLM API down, timeouts, long-running tasks, infrastructure failures, etc. Restate guarantees all tasks run to completion exactly once.
- ✅ **Recovery of previous progress**: After a failure, Restate recovers the progress the execution did before the crash. 
It persists routing decisions, tool execution outcomes, and deterministically replays them after failures, as opposed to executing them again. 
- 🧠 **Exactly-once execution** - Automatic deduplication of requests and tool executions via idempotency keys.
- 💾 **Persistent memory** - Maintain session state across infrastructure events.
The state can be queried from the outside. Stateful sessions are long-lived and can be resumed at any time.
- 🎮 **Task control** - Cancel tasks, query status, re-subscribe to ongoing tasks, and track progress across failures, time, and processes.

These benefits are best portrayed in the following patterns:

| Pattern                     | Retries & recovery | Exactly-once execution | Persistent memory | 
|-----------------------------|--------------------|------------------------|-------------------|
| Chaining LLM calls          | ✅                  | ✅                      |                   |              
| Parallelizing tool calls    | ✅                  | ✅                      |                   |              
| Dynamic routing             | ✅                  | ✅                      |                   |              
| Orchestrator-worker pattern | ✅                  | ✅                      |                   |              
| Evaluator-optimizer pattern | ✅                  | ✅                      |                   |              
| Human-in-the-loop pattern   | ✅                  | ✅                      | ✅                 |              


## Running the examples

1. Export your OpenAI or Anthrophic API key as an environment variable:
    ```shell
    export OPENAI_API_KEY=your_openai_api_key
    ```
    or:
    ```shell
    export ANTHROPIC_API_KEY=your_anthropic_api_key
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

Refine the results by calling the LLM iteratively with its own output.

In the UI (`http://localhost:9070`), click on the `run` handler of the `CallChainingService` to open the playground and send a default request:
<img src="https://raw.githubusercontent.com/restatedev/ai-examples/refs/heads/main/doc/img/patterns/chaining_playground.png" alt="Chaining LLM calls - UI"/>

You see in the Invocations Tab of the UI how the LLM is called multiple times, and how the results are refined step by step:

<img src="https://raw.githubusercontent.com/restatedev/ai-examples/refs/heads/main/doc/img/patterns/chaining.png" alt="Chaining LLM calls - UI"/>

### Parallelizing tool calls
[<img src="https://raw.githubusercontent.com/restatedev/img/refs/heads/main/show-code.svg">](app/parallelization.py)

Call multiple tools in parallel and wait for their results in a durable way. Tool calls are retried if they fail, and the results are persisted.

In the UI (`http://localhost:9070`), click on the `analyze_text` handler of the `ParallelizationService` to open the playground and send a default request:
<img src="https://raw.githubusercontent.com/restatedev/ai-examples/refs/heads/main/doc/img/patterns/parallel_playground.png" alt="Parallel LLM calls - UI"/>


You see in the UI how the different tasks are executed in parallel: 

<img src="https://raw.githubusercontent.com/restatedev/ai-examples/refs/heads/main/doc/img/patterns/parallel.png" alt="Parallel LLM calls - UI"/>

Once all tasks are done, the results are aggregated and returned to the client.

### Dynamic routing to tools based on LLM output
[<img src="https://raw.githubusercontent.com/restatedev/img/refs/heads/main/show-code.svg">](app/routing_to_tool.py)

Route the execution to different tools based on the LLM's output. Routing decisions are persisted and can be retried.

In the UI (`http://localhost:9070`), click on the `route` handler of the `ToolRouterService` to open the playground and send a default request:
<img src="https://raw.githubusercontent.com/restatedev/ai-examples/refs/heads/main/doc/img/patterns/route-to-tools-playground.png" alt="Dynamic routing LLM calls - UI"/>

In the UI, you can see how the LLM decides to forward the request to the technical support tools, and how the response is processed:

<img src="https://raw.githubusercontent.com/restatedev/ai-examples/refs/heads/main/doc/img/patterns/route-to-tools.png" alt="Dynamic routing based on LLM output - UI"/>

### Dynamic routing to agents based on LLM output
[<img src="https://raw.githubusercontent.com/restatedev/img/refs/heads/main/show-code.svg">](app/routing_to_agent.py)

Route the execution to specialized agents based on the LLM's output. Routing decisions are persisted and can be retried.

In the UI (`http://localhost:9070`), click on the `route` handler of the `AgentRouterService` to open the playground and send a default request:
<img src="https://raw.githubusercontent.com/restatedev/ai-examples/refs/heads/main/doc/img/patterns/route-to-agent-playground.png" alt="Dynamic routing LLM calls - UI"/>

In the UI, you can see how the LLM decides to forward the request to the specialized support agents, and how the response is processed:

<img src="https://raw.githubusercontent.com/restatedev/ai-examples/refs/heads/main/doc/img/patterns/route-to-agent.png" alt="Dynamic routing based on LLM output - UI"/>

### Orchestrator-worker pattern
[<img src="https://raw.githubusercontent.com/restatedev/img/refs/heads/main/show-code.svg">](orchestrator_workers/service.py)

A resilient orchestration workflow in which a central LLM dynamically breaks down tasks, delegates them to worker LLMs, and analyzes their results.

In the UI (`http://localhost:9070`), click on the `process_text` handler of the `Orchestrator` to open the playground and send a default request:
<img src="https://raw.githubusercontent.com/restatedev/ai-examples/refs/heads/main/doc/img/patterns/orchestrator-playground.png" alt="Orchestrator LLM calls - UI"/>

In the UI, you can see how the LLM split the task in three parts and how each of the worker LLMs execute their tasks in parallel:
<img src="https://raw.githubusercontent.com/restatedev/ai-examples/refs/heads/main/doc/img/patterns/orchestrator.png" alt="Orchestrator-worker pattern - UI"/>

### Evaluator-optimizer pattern
[<img src="https://raw.githubusercontent.com/restatedev/img/refs/heads/main/show-code.svg">](evaluator_optimizer/service.py)

Let the LLM generate a response, and ask another LLM to evaluate the response, and let them iterate on it.

Send an HTTP request to the service by running the [client](evaluator_optimizer/client.py):

```shell
uv run evaluator_client
```

<img src="https://raw.githubusercontent.com/restatedev/ai-examples/refs/heads/main/doc/img/patterns/evaluator.png" alt="Evaluator-optimizer pattern - UI"/>


### Human-in-the-loop pattern

An LLM generates a response, and then a human can review and approve the response before the LLM continues with the next step.

#### Option 1: `run_with_promise` handler
[<img src="https://raw.githubusercontent.com/restatedev/img/refs/heads/main/show-code.svg">](human_in_the_loop/service.py)

This handler gathers human feedback by blocking the generation-evaluation loop on a Promise that gets resolved with human feedback.

This is a **Durable Promise**, meaning that the promise can be recovered across processes and time. The Promise is persisted inside Restate. 

Test this out by killing the service halfway through or restarting the Restate Server. You will notice that Restate will still be able to resolve the promise and invoke the handler again.

```shell
curl localhost:8080/HumanInTheLoopService/giselle/run_with_promise \
    --json '"Write a poem about Durable Execution"'
```

Then use the printed curl command to incorporate external feedback. And supply `PASS` as feedback to accept the solution.

You can see how the feedback gets incorporated in the Invocations tab in the Restate UI (`http://localhost:9070`):

<img src="https://raw.githubusercontent.com/restatedev/ai-examples/refs/heads/main/doc/img/patterns/human_in_the_loop.png" alt="Human-in-the-loop pattern - UI"/>


#### Option 2: `run` handler
[<img src="https://raw.githubusercontent.com/restatedev/img/refs/heads/main/show-code.svg">](human_in_the_loop/service.py)

Repeatedly invoke the handler with feedback until the response is satisfactory.

This is useful when the person providing feedback is the same as the one generating the response.

Restate keeps the state 

Use the UI playground to test the human-in-the-loop.
1. Go to the Restate UI at `http://localhost:9070`
2. Click on the `HumanInTheLoopService` and then on the `Playground` button.
3. Select the `run` handler and send it a message. For example:

   <img src="https://raw.githubusercontent.com/restatedev/ai-examples/refs/heads/main/doc/img/patterns/human_in_the_loop.png" alt="Human-in-the-loop" width="900px"/>

4. You can then provide feedback on the response and send it back to the handler.

   <img src="https://raw.githubusercontent.com/restatedev/ai-examples/refs/heads/main/doc/img/patterns/human_in_the_loop_2.png" alt="Human-in-the-loop" width="900px"/>


Alternatively, you can use `curl`:
```shell
curl localhost:8080/HumanInTheLoopService/giselle/run --json '"Write a poem about Durable Execution"'
```

And repeatedly do the same to provide feedback.