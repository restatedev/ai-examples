# Patterns for building resilient LLM-based apps and agents with Restate

These patterns show how you can use Restate to harden LLM-based routing decisions and tool executions.

They do not implement end-to-end agents, but serve as small self-contained patterns that can be mixed and matched to build more complex workflows.

The patterns included here:
- [Chaining LLM calls](app/chaining.py): Refine the results by calling the LLM iteratively with its own output.
- [Parallelizing tool calls](app/parallelization.py): Call multiple tools in parallel and wait for their results in a durable way. Tool calls are retried if they fail, and the results are persisted.
- [Dynamic tool routing based on LLM output](app/routing_to_tool.py): Route the execution to different tools based on the LLM's output. Routing decisions are persisted and can be retried.
- [Multi-agent routing based on LLM output](app/routing_to_agent.py): Route the execution to specialized agents based on the LLM's output. Routing decisions are persisted and can be retried.
- [Orchestrator-worker pattern](app/orchestrator_workers.py): A resilient orchestration workflow in which a central LLM dynamically breaks down tasks, delegates them to worker LLMs, and analyzes their results.
- [Evaluator-optimizer pattern](app/evaluator_optimizer.py): Let the LLM generate a response, and ask another LLM to evaluate the response, and let them iterate on it.
- [Human-in-the-loop pattern](app/human_in_the_loop.py): An LLM generates a response, and then a human can review and approve the response before the LLM continues with the next step.
- [Chat sessions](app/chat.py): A chat session where the state is kept across multiple requests, and where a human can provide feedback on the LLM's responses.

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
| Human-in-the-loop pattern   | ✅                  | ✅                      |                   |              
| Chat sessions               | ✅                  | ✅                      | ✅                 |              


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

### Multi-agent routing based on LLM output
[<img src="https://raw.githubusercontent.com/restatedev/img/refs/heads/main/show-code.svg">](app/routing_to_agent.py)

Route the execution to specialized agents based on the LLM's output. Routing decisions are persisted and can be retried.

In the UI (`http://localhost:9070`), click on the `route` handler of the `AgentRouterService` to open the playground and send a default request:
<img src="https://raw.githubusercontent.com/restatedev/ai-examples/refs/heads/main/doc/img/patterns/route-to-agent-playground.png" alt="Dynamic routing LLM calls - UI"/>

In the UI, you can see how the LLM decides to forward the request to the specialized support agents, and how the response is processed:

<img src="https://raw.githubusercontent.com/restatedev/ai-examples/refs/heads/main/doc/img/patterns/route-to-agent.png" alt="Dynamic routing based on LLM output - UI"/>

### Orchestrator-worker pattern
[<img src="https://raw.githubusercontent.com/restatedev/img/refs/heads/main/show-code.svg">](app/orchestrator_workers.py)

A resilient orchestration workflow in which a central LLM dynamically breaks down tasks, delegates them to worker LLMs, and analyzes their results.

In the UI (`http://localhost:9070`), click on the `process_text` handler of the `Orchestrator` to open the playground and send a default request:
<img src="https://raw.githubusercontent.com/restatedev/ai-examples/refs/heads/main/doc/img/patterns/orchestrator-playground.png" alt="Orchestrator LLM calls - UI"/>

In the UI, you can see how the LLM split the task in three parts and how each of the worker LLMs execute their tasks in parallel:
<img src="https://raw.githubusercontent.com/restatedev/ai-examples/refs/heads/main/doc/img/patterns/orchestrator.png" alt="Orchestrator-worker pattern - UI"/>

### Evaluator-optimizer pattern
[<img src="https://raw.githubusercontent.com/restatedev/img/refs/heads/main/show-code.svg">](app/evaluator_optimizer.py)

Let the LLM generate a response, and ask another LLM to evaluate the response, and let them iterate on it.

In the UI (`http://localhost:9070`), click on the `improve_until_good` handler of the `EvaluatorOptimizer` to open the playground and send a default request:
<img src="https://raw.githubusercontent.com/restatedev/ai-examples/refs/heads/main/doc/img/patterns/evaluator-playground.png" alt="Evaluator-optimizer pattern - UI"/>

In the UI, you can see how the LLM generates a response, and how the evaluator LLM evaluates it and asks for improvements until the response is satisfactory:
<img src="https://raw.githubusercontent.com/restatedev/ai-examples/refs/heads/main/doc/img/patterns/evaluator.png" alt="Evaluator-optimizer pattern - UI"/>


### Human-in-the-loop pattern

An LLM generates a response, and then a human can review and approve the response before the LLM continues with the next step.

#### Option 1: `run_with_promise` handler
[<img src="https://raw.githubusercontent.com/restatedev/img/refs/heads/main/show-code.svg">](app/human_in_the_loop.py)

This handler gathers human feedback by blocking the generation-evaluation loop on a Promise that gets resolved with human feedback.

This is a **Durable Promise**, meaning that the promise can be recovered across processes and time. The Promise is persisted inside Restate. 

In the UI (`http://localhost:9070`), click on the `moderate` handler of the `HumanInTheLoopService` to open the playground and send a default request:
<img src="https://raw.githubusercontent.com/restatedev/ai-examples/refs/heads/main/doc/img/patterns/human-in-the-loop-playground.png" alt="Human-in-the-loop pattern - UI"/>

Test this out by killing the service halfway through or restarting the Restate Server. You will notice that Restate will still be able to resolve the promise and invoke the handler again.

Then use the **curl command printed in the service logs** to provide your feedback.

You can see how the feedback gets incorporated in the Invocations tab in the Restate UI (`http://localhost:9070`):

<img src="https://raw.githubusercontent.com/restatedev/ai-examples/refs/heads/main/doc/img/patterns/human-in-the-loop.png" alt="Human-in-the-loop pattern - UI"/>


### Long-lived, stateful Chat sessions
[<img src="https://raw.githubusercontent.com/restatedev/img/refs/heads/main/show-code.svg">](app/chat.py)

A chat session where the state is kept across multiple requests, and where a human can provide feedback on the LLM's responses.

Restate keeps the state. 

In the UI (`http://localhost:9070`), click on the `message` handler of the `Chat` service to open the playground and send a default request:

<img src="https://raw.githubusercontent.com/restatedev/ai-examples/refs/heads/main/doc/img/patterns/chat-1.png" alt="Chat" width="900px"/>

You can then provide feedback on the response by sending new messages to the same session:

<img src="https://raw.githubusercontent.com/restatedev/ai-examples/refs/heads/main/doc/img/patterns/chat-2.png" alt="Chat" width="900px"/>

In the invocations tab, you can see how the memory was loaded and stored in Restate:
<img src="https://raw.githubusercontent.com/restatedev/ai-examples/refs/heads/main/doc/img/patterns/chat.png" alt="Chat - UI"/>

Go to the state tab of the UI to see the state of the chat session:
<img src="https://raw.githubusercontent.com/restatedev/ai-examples/refs/heads/main/doc/img/patterns/chat-state.png" alt="Chat" width="900px"/>
