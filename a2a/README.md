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
- Access to an LLM and API Key
  - Restate Reimbursement Agent: [OpenAI API Key](https://platform.openai.com/docs/api-reference/authentication)
    ```shell
    echo "OPENAI_API_KEY=your_api_key_here" >> .env
    ```
  - Other agents: [Google API Key](https://ai.google.dev/gemini-api/docs/api-key)
    ```shell
    echo "GOOGLE_API_KEY=your_api_key_here" >> .env
    ```

## Running the example: Single agent

This example shows how to run a single agent and use the A2A protocol to communicate with it.

1. [Start the Restate Server](https://docs.restate.dev/develop/local_dev) in a separate shell:
    ```shell
    restate-server
    ```

2. Start one of the agents, including their A2A server:
   - **Restate Reimbursement Agent**: Run the Restate agent ([`agents/restatedev`](agents/restatedev/__main__.py)), if you want an agent with end-to-end durability for the agent loop and full observability of what the agent executes. The reimburse tool implements a long-running workflow that waits on a human approval:
       ```shell
       uv run agents/restatedev
       ```
     Then register the service:
       ```shell
       restate -y deployments register http://localhost:9081/restate/v1
       ```
   - **Google ADK Reimbursement Agent**: To run an agent that uses the Google ADK ([`agents/google_adk`](agents/google_adk/__main__.py)):
       ```shell
       uv run agents/google_adk
       ```
     Then register the service:
       ```shell
       restate -y deployments register http://localhost:9083/restate/v1
       ```
   - **LangGraph Currency Agent**: To run an agent that uses the LangGraph SDK ([`agents/langgraph`](agents/langgraph/__main__.py)):
       ```shell
       uv run agents/langgraph
       ```
     Then register the service:
       ```shell
       restate -y deployments register http://localhost:9082/restate/v1
       ```


You can now send A2A messages directly to agents via `curl` or the UI playground (click on your service in the overview at `localhost:9070` and then on `Playground`). 


### Send a Task to the Agent

#### Option 1: Send an A2A Task Send request to the LangGraph Currency Agent

```shell
curl localhost:8080/CurrencyAgentA2AServer/process_request \
  --json '{
    "jsonrpc": "2.0",
    "id": 67892345,
    "method":"tasks/send",
    "params": {
        "id": "unique-task-id-79051",
        "sessionId": "session-id-0135",
        "message": {
          "role":"user",
          "parts": [{
          "type":"text",
          "text": "What is the exchange rate from USD to euro?"
          }]
    },
    "metadata": {}
    }
  }' | jq .
```

<details>
<summary>View output</summary>

```json
{
  "jsonrpc": "2.0",
  "id": 67892345,
  "result": {
    "id": "unique-task-id-79051",
    "sessionId": "session-id-0135",
    "status": {
      "state": "completed",
      "message": null,
      "timestamp": "2025-05-21T09:38:05.097677"
    },
    "artifacts": [
      {
        "name": null,
        "description": null,
        "parts": [
          {
            "type": "text",
            "text": "The exchange rate from USD to EUR is 0.8896. That means 1 USD is equivalent to 0.8896 EUR.",
            "metadata": null
          }
        ],
        "metadata": null,
        "index": 0,
        "append": null,
        "lastChunk": null
      }
    ],
    "history": [
      {
        "role": "user",
        "parts": [
          {
            "type": "text",
            "text": "What is the exchange rate from USD to euro?",
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

If you send the same task twice, the second attempt will get resolved immediately with the response of the first attempt.
The Restate A2A server automatically takes care of the deduplication.

#### Option 2:  Send a Task to the Google ADK Reimbursement Agent

```shell
curl localhost:8080/GoogleReimbursementAgentA2AServer/process_request \
    --json '{
      "jsonrpc": "2.0",
      "id": 2223,
      "method":"tasks/send",
      "params": {
        "id": "lwp13w5e3sdf258t3wesf13234",
        "sessionId": "lw33sl5e-8966-6g6k-26ee-2d5e6w29ya3423",
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

<details>
<summary>View output</summary>

```json
{
  "jsonrpc": "2.0",
  "id": 2223,
  "result": {
    "id": "lwp13w5e3sdf258t3wesf13234",
    "sessionId": "lw33sl5e-8966-6g6k-26ee-2d5e6w29ya3423",
    "status": {
      "state": "completed",
      "message": null,
      "timestamp": "2025-05-21T09:38:54.553926"
    },
    "artifacts": [
      {
        "name": null,
        "description": null,
        "parts": [
          {
            "type": "text",
            "text": "Your reimbursement request with request ID `request_id_9559913` has been approved.\n",
            "metadata": null
          }
        ],
        "metadata": null,
        "index": 0,
        "append": null,
        "lastChunk": null
      }
    ],
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

#### Option 3:  Send a Task to the Restate Reimbursement Agent

If you use the Restate Reimbursement Agent, then this task will block on a human approval if the amount is greater than 100 USD.


```shell
curl localhost:8080/ReimbursementAgentA2AServer/process_request \
    --json '{
      "jsonrpc": "2.0",
      "id": 2223,
      "method":"tasks/send",
      "params": {
        "id": "lwp13w5e3sdf258t3wesf13234",
        "sessionId": "lw33sl5e-8966-6g6k-26ee-2d5e6w29ya3423",
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

While the task is waiting on human approval, you can have a look at the Restate UI at http://localhost:9070/ui/invocations to see the task progress:

<img src="img/restate_ui_journal.png" alt="Restate UI" width="1000"/>

#### Get a Task

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

<img src="img/restate_ui_task_state.png" alt="Restate UI" width="1000"/>

#### Cancel a Task

```shell
curl localhost:8080/ReimbursementAgentA2AServer/process_request \
    --json '{
      "jsonrpc": "2.0",
      "id": 3,
      "method":"tasks/cancel",
      "params": {
        "id": "lwp13w5e3sdf258t3wesf13234",
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

This is implemented via Restate's [cancel task API](https://docs.restate.dev/develop/python/service-communication#cancel-an-invocation).

## Running the example: multi-agent 

This example shows how to run multiple agents and use the A2A protocol to communicate with them.

<img src="img/multi_agent.png" alt="Restate UI" width="600"/>

Make sure you have no other Restate server/services running. Then bring up the multi-agent example **from the root of the repository**:

```shell
docker compose -f a2a/compose.yml up
```

Go to the Restate UI ([`http://localhost:9070`](`http://localhost:9070`)). You see here the overview of the services that are running:

<img src="img/multi_agent_overview.png" alt="Restate UI" width="1000"/>

To send messages to the host agent, click on it and then click on the "Playground" button. 

<img src="img/multi_agent_chat.png" alt="Restate UI" width="1000"/>

The host agent will forward messages to the registered agents that it knows of, and it will use the A2A protocol to communicate with them.

You can see in the Restate UI to which agents your host agent has access. For `my-user`, we have access to the following:

<img src="img/multi_agent_list.png" alt="Restate UI" width="1000"/>


To bring the services down, run:

```shell
docker compose -f a2a/compose.yml down
docker compose -f a2a/compose.yml rm
```

