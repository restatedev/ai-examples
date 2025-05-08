# Restate A2A Agents

This repo shows how to build agents with [Restate](https://restate.dev/) and the [A2A protocol](https://google.github.io/A2A/).

- [A2A server and Durable Task Object](common/server/a2a_server.py)
- [Example agents](agents/)

This repo contains two different types of agent implementations:
1. Using Restate for the A2A Server and Durable Task Object. And using an Agent SDK like Google ADK for the agent implementation.
2. Using Restate for the A2A Server, Durable Task Object, and agent implementation. 

## Prerequisites

- Python 3.13 or higher
- uv


## Host agent demo

### 1. Run the A2A server and agent

You can either run an agent that uses the Google ADK or an agent that uses the Restate agent SDK.

If you want to get workflow-like resiliency and observability for the entire agentic workflow, you should use the Restate agent SDK.


####  Start the agents:

Reimbursement agent with Restate:
```shell
uv run agents/restate
```

or use the Reimbursement agent with Restate and the Google ADK
```shell
uv run agents/google_adk
``` 


Also start the LangGraph agent:
```shell
uv run agents/langgraph
```


### 2. Start the Restate Server

Start the Restate Server with npx or Docker ([for other options check the docs](https://docs.restate.dev/develop/local_dev#running-restate-server--cli-locally)). 

#### Option 1: with npx

```shell
npx @restatedev/restate-server
```

Let Restate know where the A2A server is running:

```shell
npx @restatedev/restate deployments register http://localhost:9081
npx @restatedev/restate deployments register http://localhost:9083
```

#### Option 2: with Docker

```shell
docker run --name restate_dev --rm -p 8080:8080 -p 9070:9070 -p 9071:9071 \
  --add-host=host.docker.internal:host-gateway docker.restate.dev/restatedev/restate:1.3
```

Let Restate know where the A2A server is running:
```shell
docker run -it --network=host docker.restate.dev/restatedev/restate-cli:1.3 \
  deployments register http://host.docker.internal:9081
docker run -it --network=host docker.restate.dev/restatedev/restate-cli:1.3 \
  deployments register http://host.docker.internal:9083
```

## Start the host agent

```
uv run agents/host_agent
```

Register the host agent at port 9080

## Talk to the host agent 

Go to the Restate UI, click on the host agent, then click on the "Playground" button. From there, you can send messages to the host agent directly through the Restate UI.

The host agent will forward messages to the registered agents that it knows of, and it will use the A2A protocol to communicate with them. Ensure that the agents are properly registered and running before interacting with the host agent.


-----------------------------------------------------------------------------------------------

## Other Experiments

### Sending A2A Messages to Agents Directly

You can send A2A messages directly to agents without going through the host agent. 

This allows you to bypass the host agent and communicate in the A2A protocol with the agents. 

#### Example: Send a Message to the Reimbursement Agent

```shell
curl localhost:8080/ReimbursementAgentA2AServer/process_request \
  --json '{
    "jsonrpc": "2.0",
    "id": 12345,
    "method":"tasks/send",
    "params": {
    "id": "unique-task-id-123",
    "sessionId": "session-id-456",
    "message": {
      "role":"user",
      "parts": [{
      "type":"text",
      "text": "Reimburse my flight ticket for 500USD."
      }]
    },
    "metadata": {}
    }
  }' | jq .
```

#### Example: Send a Message to the LangGraph Agent

```shell
curl localhost:8080/CurrencyAgentA2AServer/process_request \
  --json '{
    "jsonrpc": "2.0",
    "id": 67892,
    "method":"tasks/send",
    "params": {
    "id": "unique-task-id-790",
    "sessionId": "session-id-013",
    "message": {
      "role":"user",
      "parts": [{
      "type":"text",
      "text": "Convert 10 US dollars into euros."
      }]
    },
    "metadata": {}
    }
  }' | jq .
```



## Get Agent Card

```shell
curl localhost:8080/ReimbursementAgentA2AServer/get_agent_card | jq .
```

## Send a Task


```shell
curl localhost:8080/ReimbursementAgentA2AServer/process_request \
    --json '{
      "jsonrpc": "2.0",
      "id": 2223,
      "method":"tasks/send",
      "params": {
        "id": "lwp13w5e3sdf258t3wesf1323",
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

**For the Restate agent:**
This task will block on a human approval since the amount is greater than 100 USD.
The logs of the agent service will print the curl command to approve the reimbursement and unblock the task. 

While the task is waiting on human approval, you can have a look at the Restate UI at http://localhost:9070/ui/invocations to see the task progress:

<img src="img/restate_ui_journal.png" alt="Restate UI" width="1000"/>

## Get a Task

```shell
curl localhost:8080/ReimbursementAgentA2AServer/process_request \
    --json '{
      "jsonrpc": "2.0",
      "id": 2,
      "method":"tasks/get",
      "params": {
        "id": "lwp13w5e3sdf258t3wesf13",
        "historyLength": 10,
        "metadata": {}
      }
    }' | jq . 
```

The Durable Task Object stores the Task data in Restate's embedded K/V store. 

We can query the K/V store via the UI. Have a look at the task progress in the Restate UI at http://localhost:9070/ui/state:

<img src="img/restate_ui_task_state.png" alt="Restate UI" width="1000"/>

## Cancel a Task

```shell
curl localhost:8080/ReimbursementAgentA2AServer/process_request \
    --json '{
      "jsonrpc": "2.0",
      "id": 3,
      "method":"tasks/cancel",
      "params": {
        "id": "lwp13w5e3sdf258t3wesf1323",
        "metadata": {}
      }
    }' | jq . 
```

## Set Task Push Notifications

```shell
curl localhost:8080/ReimbursementAgentA2AServer/process_request \
    --json '{
      "jsonrpc": "2.0",
      "id": 5,
      "method":"tasks/pushNotification/set",
      "params": {
        "id": "8b9f4c2703648d68b9123",
        "pushNotificationConfig": {
          "url": "https://example.com/callback",
          "authentication": {
            "schemes": ["jwt"]
          }
        }
      }
    }' | jq . 
```

## Get Task Push Notifications

```shell
curl localhost:8080/ReimbursementAgentA2AServer/process_request \
    --json '{
      "jsonrpc": "2.0",
      "id": 6,
      "method":"tasks/pushNotification/get",
      "params": {
        "id": "8b9f4c2703648d68b9123"
      }
    }' | jq . 
```

