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
echo "OPENAI_API_KEY=your_api_key_here" >> .env
docker compose up
```

(It will take a while before all the services are up and running and you will see a few retries for the registration.)

Go to the Restate UI (`http://localhost:9070`). You see here the overview of the services that are running:

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
  "id": 142,
  "method": "message/send",
  "params": {
    "message": {
      "role": "user",
      "parts": [
        {
          "kind": "text",
          "text": "What is the weather in Detroit?"
        }
      ],
      "messageId": "92249e7702-767c-417b-a0b0-f0741243c589"
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
  "id": 14243,
  "method": "message/send",
  "params": {
    "message": {
      "role": "user",
      "parts": [
        {
          "kind": "text",
          "text": "Reimburse my hotel for my business trip of 5 nights for 1200USD"
        }
      ],
      "messageId": "92249e73702-7674c-417b-a0b0-f0741243c589"
    },
    "metadata": {}
  }
}' | jq . 
```

It will then return a response mentioning you need to provide a date. 

<details><summary>View output</summary>

```json
{
  "id": 1423,
  "jsonrpc": "2.0",
  "result": {
    "artifacts": null,
    "contextId": "5e00b3a6-dcc7-43ee-a389-0e2a65958444",
    "history": [
      {
        "contextId": "5e00b3a6-dcc7-43ee-a389-0e2a65958444",
        "extensions": null,
        "kind": "message",
        "messageId": "92249e73702-767c-417b-a0b0-f0741243c589",
        "metadata": null,
        "parts": [
          {
            "kind": "text",
            "metadata": null,
            "text": "Reimburse my hotel for my business trip of 5 nights for 1200USD"
          }
        ],
        "referenceTaskIds": null,
        "role": "user",
        "taskId": null
      }
    ],
    "id": "92249e73702-767c-417b-a0b0-f0741243c589",
    "kind": "task",
    "metadata": null,
    "status": {
      "message": {
        "contextId": null,
        "extensions": null,
        "kind": "message",
        "messageId": "1accd046-5ba4-4c13-b0eb-fcad422fcea7",
        "metadata": null,
        "parts": [
          {
            "kind": "text",
            "metadata": null,
            "text": "MISSING_INFO:Please provide the date of the transaction."
          }
        ],
        "referenceTaskIds": null,
        "role": "agent",
        "taskId": null
      },
      "state": "input-required",
      "timestamp": "2025-11-06T14:47:37.430346"
    }
  }
}

```

</details>

You can then provide the date of the transaction by sending another request to the same stateful session (same task and session ID):

```shell
curl localhost:8080/ReimbursementAgentA2AServer/process_request \
    --json '{
  "jsonrpc": "2.0",
  "id": 1423,
  "method": "message/send",
  "params": {
    "message": {
      "contextId": "5e00b3a6-dcc7-43ee-a389-0e2a65958444",
      "role": "user",
      "parts": [
        {
          "kind": "text",
          "text": "The date of the transaction is 05/04/2025"
        }
      ],
      "messageId": "92249e73702-767c-417b-a0b0-f0741243c589"
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
      "method": "message/send",
      "params": {
        "message": {
          "contextId": "5e00b3a6-dcc7-43ee-a389-0e2a65958444",
          "role":"user",
          "parts": [{
            "kind": "text",
            "text": "The info looks good"
          }]
          "messageId": "92249e737032-767c-417b-a0b0-f0741243c589"
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

You can have a look at the Restate UI at `http://localhost:9070/ui/invocations` to see the end-to-end flow:

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
        "id": "101496f4-7805-473c-9b15-c0f0bdff465a",
        "history_length": 10,
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
We can query the K/V store via the UI. Have a look at the task progress in the Restate UI at `http://localhost:9070/ui/state`:

<img src="https://raw.githubusercontent.com/restatedev/ai-examples/refs/heads/main/doc/img/a2a/restate_ui_task_state.png" alt="Restate UI" width="1000"/>

#### Cancel a Task

For example, start a new reimbursement task and then cancel it:

```shell
curl localhost:8080/ReimbursementAgentA2AServer/process_request \
    --json '{
  "jsonrpc": "2.0",
  "id": 1424443,
  "method": "message/send",
  "params": {
    "message": {
      "role": "user",
      "parts": [
        {
          "kind": "text",
          "text": "Reimburse my hotel for my business trip of 5 nights for 1200USD of 05/04/2025"
        }
      ],
      "messageId": "92249e73702-7674c-417b-a0b0-f0741243c449",
      "taskId": "33349e73702-7674c-417b-a0b0-f0741243c333"
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
        "id": "33349e73702-7674c-417b-a0b0-f0741243c333"
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
