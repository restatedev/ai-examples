# Resilient A2A Agents with Restate

These examples use [Restate](https://ai.restate.dev/) to implement the [Agent2Agent (A2A) protocol](https://github.com/google/A2A).

Restate acts as a scalable, resilient task orchestrator that speaks the A2A protocol and gives you:
- 🔁 **Automatic retries** - Handles LLM API downtime, timeouts, and infrastructure failures
- 🔄 **Smart recovery** - Preserves progress across failures without duplicating work
- ⏱️ **Persistent task handles** - Tracks progress across failures, time, and processes
- 🎮 **Task control** - Cancel tasks, query status, re-subscribe to ongoing tasks
- 🧠 **Idempotent submission** - Automatic deduplication based on task ID
- 🤖 **Agentic workflows** - Build resilient agents with human-in-the-loop and parallel tool execution
- 💾 **Durable state** - Maintain consistent agent state across infrastructure events
- 👀 **Full observability** - Line-by-line execution tracking with built-in audit trail
- ☁️️ **Easy to self-host** - or connect to Restate Cloud

<img src="https://raw.githubusercontent.com/restatedev/img/refs/heads/main/a2a/a2a.png" width="600px"/>

## Prerequisites
- Python 3.12 or higher
- [UV](https://docs.astral.sh/uv/)
- An [OpenAI API Key](https://platform.openai.com/docs/api-reference/authentication)
    ```shell
    echo "OPENAI_API_KEY=your_api_key_here" >> .env
    ```

## Running the example: multi-agent 

This example shows how to run multiple agents and use the A2A protocol to communicate with them.

<img src="https://raw.githubusercontent.com/restatedev/ai-examples/refs/heads/main/doc/img/a2a/multi_agent.png" alt="Restate UI" width="600"/>

Make sure you have no other Restate server/services running. Then bring up the multi-agent example:

```shell
docker compose up
```

(It will take a while before all the services are up and running and you will see a few retries for the registration.)

Go to the Restate UI ([`http://localhost:9070`](`http://localhost:9070`)). You see here the overview of the services that are running:

<img src="https://raw.githubusercontent.com/restatedev/ai-examples/refs/heads/main/doc/img/a2a/multi_agent_overview.png" alt="Restate UI" width="1000"/>

To send messages to the host agent, click on it and then click on the "Playground" button. 

<img src="https://raw.githubusercontent.com/restatedev/ai-examples/refs/heads/main/doc/img/a2a/multi_agent_chat.png" alt="Restate UI" width="1000"/>

The host agent will forward messages to the registered agents that it knows of, and it will use the A2A protocol to communicate with them.

You can also send messages with the A2A protocol directly to the agents, without going through the host agent:


### Weather Agent: Restate + OpenAI Agent SDK

You can either send a message to the weather agent using the A2A protocol:

```shell
curl localhost:8080/WeatherAgentA2AServer/process_request \
    --json '{
      "jsonrpc": "2.0",
      "id": 923043,
      "method":"tasks/send",
      "params": {
        "id": "3954039823504",
        "sessionId": "lw33sl5e-8966-6g6k-26ee-2d5e6w29ya3423",
        "message": {
          "role":"user",
          "parts": [{
            "type":"text",
            "text": "What is the weather in Detroit?"
          }]
        },
        "metadata": {}
      }
    }' | jq . 
```

### Reimbursement Agent: Restate + OpenAI Agent SDK

This is a stateful agent which runs long-running tasks and blocks on human approval if the amount is greater than 100 USD.

You talk to a dedicated reimbursement agent based on the session ID. 
If you provide the session ID, the agent will remember the conversation and the tasks you have sent to it.

To start a task that **will block on human approval**, run the following command:

```shell
curl localhost:8080/ReimbursementAgentA2AServer/process_request \
    --json '{
      "jsonrpc": "2.0",
      "id": 22323,
      "method":"tasks/send",
      "params": {
        "id": "lwp13w5e3sdf258t3wedsf13234",
        "sessionId": "lw33sl5e-8966-6g6k-26ee-2d5e6w29y3a3423",
        "message": {
          "role":"user",
          "parts": [{
            "type":"text",
            "text": "Reimburse my hotel for my business trip of 5 nights for 1200USD"
          }]
        },
        "metadata": {}
      }
    }' | jq . 
```

It will then return a response mentioning you need to provide a date. 

<details><summary>View output</summary>

```json
{
  "jsonrpc": "2.0",
  "id": 22323,
  "result": {
    "id": "lwp13w5e3sdf258t3wedsf13234",
    "sessionId": "lw33sl5e-8966-6g6k-26ee-2d5e6w29y3a3423",
    "status": {
      "state": "input-required",
      "message": {
        "role": "agent",
        "parts": [
          {
            "type": "text",
            "text": "MISSING_INFO: Could you please provide the date of the transaction for the hotel reimbursement?",
            "metadata": null
          }
        ],
        "metadata": null
      },
      "timestamp": "2025-06-18T08:56:41.037053"
    },
    "artifacts": null,
    "history": [
      {
        "role": "user",
        "parts": [
          {
            "type": "text",
            "text": "Reimburse my hotel for my business trip of 5 nights for 1200USD",
            "metadata": null
          }
        ],
        "metadata": null
      }
    ],
    "metadata": null
  },
  "error": null
}
```

</details>

You can then provide the date of the transaction by sending another request to the same stateful session (same task and session ID):

```shell
curl localhost:8080/ReimbursementAgentA2AServer/process_request \
    --json '{
      "jsonrpc": "2.0",
      "id": 22324,
      "method":"tasks/send",
      "params": {
        "id": "lwp13w5e3sdf258t3wedsf13234",
        "sessionId": "lw33sl5e-8966-6g6k-26ee-2d5e6w29y3a3423",
        "message": {
          "role":"user",
          "parts": [{
            "type":"text",
            "text": "The date of the transaction is 05/04/2025"
          }]
        },
        "metadata": {}
      }
    }' | jq . 
```

Possibly, the agent will ask for a final approval before it can proceed with the reimbursement. 
```shell
curl localhost:8080/ReimbursementAgentA2AServer/process_request \
    --json '{
      "jsonrpc": "2.0",
      "id": 22325,
      "method":"tasks/send",
      "params": {
        "id": "lwp13w5e3sdf258t3wedsf13234",
        "sessionId": "lw33sl5e-8966-6g6k-26ee-2d5e6w29y3a3423",
        "message": {
          "role":"user",
          "parts": [{
            "type":"text",
            "text": "The info looks good"
          }]
        },
        "metadata": {}
      }
    }' | jq . 
```

Once the agent has all the information, it will ask start the reimbursement process and will block until a human approves the request.

The logs of the agent service will print the curl command to approve the reimbursement and unblock the task.
Or you can leave the task blocked if you want to try out the get and cancel task commands below.

```text
... first part of logs ...
[2025-05-16 13:42:50,410] [310993] [INFO] - Agent session lwp13w5e3sdf258t3wesf13234 -   Starting iteration of agent loop with agent: ReimbursementAgent and tools/handoffs: ['create_request_form', 'reimburse', 'return_form']
[2025-05-16 13:42:50,410] [310993] [INFO] - Agent session lwp13w5e3sdf258t3wesf13234 -  Calling LLM
[2025-05-16 13:42:52,293] [310993] [INFO] - HTTP Request: POST https://api.openai.com/v1/responses "HTTP/1.1 200 OK"
[2025-05-16 13:42:52,303] [310993] [INFO] - Agent session lwp13w5e3sdf258t3wesf13234 -  Executing tool reimburse
================================================== 
 Requesting approval for request_id_1633297 
 Resolve via: 
curl localhost:8080/restate/awakeables/sign_1oqmHpDF_RJQBltjnf48zszmfmRr4w9izAAAAEQ/resolve --json '{"approved": true}' 
 ==================================================
```

Approve the reimbursement. 

You can have a look at the Restate UI at http://localhost:9070/ui/invocations to see the end-to-end flow:

<img src="https://raw.githubusercontent.com/restatedev/ai-examples/refs/heads/main/doc/img/a2a/long-running-task.png" alt="Restate UI" width="1200"/>

We see how the A2A server called the task object. The task object then called the `invoke` method of the reimbursement agent, which then called the LLM to process the request.
We see how it waited for the human approval and then continued with the reimbursement process. 

Finally, it scheduled the payment task to execute at the end of the month.

**You can now also use the A2A protocol to query the task status and history, or cancel the task:**

#### Get the task

```shell
curl localhost:8080/ReimbursementAgentA2AServer/process_request \
    --json '{
      "jsonrpc": "2.0",
      "id": 2,
      "method":"tasks/get",
      "params": {
        "id": "lwp13w5e3sdf258t3wesf13234",
        "historyLength": 10,
        "metadata": {}
      }
    }' | jq . 
```

<details>
<summary>View output</summary>

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "id": "lwp13w5e3sdf258t3wesf13234",
    "sessionId": "lw33sl5e-8966-6g6k-26ee-2d5e6w29ya3423",
    "status": {
      "state": "submitted",
      "message": null,
      "timestamp": "2025-05-16T13:42:46.306507"
    },
    "artifacts": null,
    "history": [
      {
        "role": "user",
        "parts": [
          {
            "type": "text",
            "text": "Reimburse my hotel for my business trip of 5 nights for 1200USD of 05/04/2025",
            "metadata": null
          }
        ],
        "metadata": null
      }
    ],
    "metadata": null
  },
  "error": null
}
```

</details>

The Durable Task Object stores the Task data in Restate's embedded K/V store.
We can query the K/V store via the UI. Have a look at the task progress in the Restate UI at http://localhost:9070/ui/state:

<img src="https://raw.githubusercontent.com/restatedev/ai-examples/refs/heads/main/doc/img/a2a/restate_ui_task_state.png" alt="Restate UI" width="1000"/>

#### Cancel a Task

For example, start a new reimbursement task and then cancel it:

```shell
curl localhost:8080/ReimbursementAgentA2AServer/process_request \
    --json '{
      "jsonrpc": "2.0",
      "id": 223235,
      "method":"tasks/send",
      "params": {
        "id": "lwp13w5e3sdf258t3wedsf13234",
        "sessionId": "lw33sl5e-8966-6g6k-26ee-2d5e6w29y3a34235",
        "message": {
          "role":"user",
          "parts": [{
            "type":"text",
            "text": "Reimburse my hotel for my business trip of 5 nights for 1200USD of 05/04/2025"
          }]
        },
        "metadata": {}
      }
    }' | jq . 
```

```shell
curl localhost:8080/ReimbursementAgentA2AServer/process_request \
    --json '{
      "jsonrpc": "2.0",
      "id": 3,
      "method":"tasks/cancel",
      "params": {
        "id": "lwp13w5e3sdf258t3wedsf13234",
        "metadata": {}
      }
    }' | jq . 
```

<details>
<summary>View output</summary>

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "result": {
    "id": "lwp13w5e3sdf258t3wesf13234",
    "sessionId": "lw33sl5e-8966-6g6k-26ee-2d5e6w29ya3423",
    "status": {
      "state": "canceled",
      "message": null,
      "timestamp": "2025-05-16T13:44:05.852323"
    },
    "artifacts": null,
    "history": [
      {
        "role": "user",
        "parts": [
          {
            "type": "text",
            "text": "Reimburse my hotel for my business trip of 5 nights for 1200USD of 05/04/2025",
            "metadata": null
          }
        ],
        "metadata": null
      }
    ],
    "metadata": null
  },
  "error": null
}
```

</details>

The UI also shows the task as canceled in the state tab and in the journal overview of the long-running task:

<img src="https://raw.githubusercontent.com/restatedev/ai-examples/refs/heads/main/doc/img/a2a/cancel_journal.png" alt="Restate UI" width="1200"/>

This is implemented via Restate's [cancel task API](https://docs.restate.dev/develop/python/service-communication#cancel-an-invocation).

### Stopping the example

To bring the services down, run:

```shell
docker compose down
docker compose rm
```


## Running a single agent

You can also start a single agent together with Restate. 


For example, to run the weather agent:

```shell
uv run a2a/weather
```

[Start the Restate Server](https://docs.restate.dev/develop/local_dev) in a separate shell:
```shell
restate-server
```

Then register the service:

```shell
restate -y deployments register http://localhost:9081/restate/v1
```

Then send requests to the agent.
