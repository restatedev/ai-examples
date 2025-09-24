# OpenAI Agents Tour - Python Edition

A comprehensive tour of OpenAI agents using Restate for durability, translated from the Vercel AI tour-of-agents examples.

This project demonstrates various agent patterns and use cases:

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- OpenAI API key (set as `OPENAI_API_KEY` environment variable)
- Restate server running (for production use)

### Installation

```shell
# Install dependencies
uv sync

# Set your OpenAI API key
export OPENAI_API_KEY="your-api-key-here"

# Run the application
uv run .
```

## 📁 Project Structure

### Chat Agents
- **`app/chat/agent.py`** - Basic conversational agent with persistent message history

### Durable Execution
- **`app/durableexecution/agent.py`** - Weather agent demonstrating durable tool execution

### Orchestration
- **`app/orchestration/multi_agent.py`** - Multi-agent system for insurance claim processing
- **`app/orchestration/sub_workflow_agent.py`** - Sub-workflow patterns with human approval

### Human-in-the-Loop
- **`app/humanintheloop/agent.py`** - Basic human approval workflow
- **`app/humanintheloop/agent_with_timeout.py`** - Human approval with timeout handling

### Advanced Patterns
- **`app/advanced/rollback_agent.py`** - Transaction-like behavior with automatic rollback
- **`app/advanced/manual_loop_agent.py`** - Manual control over agent conversation loops

### Error Handling
- **`app/errorhandling/fail_on_terminal_tool_agent.py`** - Immediate failure on terminal errors
- **`app/errorhandling/stop_on_terminal_tool_agent.py`** - Graceful handling of terminal errors

### Parallel Processing
- **`app/parallelwork/parallel_agents.py`** - Multiple agents running in parallel
- **`app/parallelwork/parallel_tools_agent.py`** - Parallel tool execution within a single agent

## 🔧 Key Features

### Durable Execution
All examples use `ctx.run_typed()` for durable execution, ensuring operations are:
- **Persistent** - Operations survive process restarts
- **Exactly-once** - No duplicate executions
- **Recoverable** - Automatic retry on transient failures

### OpenAI Integration
Each agent uses the `DurableOpenAIWrapper` class that provides:
- Automatic retry logic for OpenAI API calls
- Persistent storage of conversation state
- Durable tool execution

### Example Usage Patterns

#### Basic Chat Agent
```python
# Send a message to the chat agent
curl -X POST http://localhost:9080/Chat/conversation-1/message \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, how are you?"}'
```

#### Weather Agent
```python
# Get weather information
curl -X POST http://localhost:9080/WeatherAgent/run \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is the weather like in New York?"}'
```

#### Insurance Claim Processing
```python
# Process an insurance claim
curl -X POST http://localhost:9080/MultiAgentClaimApproval/run \
  -H "Content-Type: application/json" \
  -d '{
    "id": "claim-123",
    "amount": 2500.00,
    "description": "Water damage to kitchen",
    "claimant": "John Doe",
    "date": "2024-01-15"
  }'
```

## 🏗️ Architecture

All agents follow these principles:

1. **Stateful**: Conversation history and state persisted automatically
2. **Durable**: Operations survive failures and restarts
3. **Observable**: Full execution history tracked
4. **Scalable**: Horizontal scaling with Restate

## 🐳 Docker Support

Build and run with Docker:

```shell
docker build -t tour-of-agents .
docker run -p 9080:9080 -e OPENAI_API_KEY="your-key" tour-of-agents
```

## 📚 Learn More

Each agent demonstrates different patterns:

- **Chat**: Basic conversation management
- **Durable Execution**: Reliable external API calls
- **Orchestration**: Coordinating multiple agents/services
- **Human-in-the-Loop**: Approval workflows with timeouts
- **Advanced**: Transaction patterns and manual control
- **Error Handling**: Graceful failure management
- **Parallel Work**: Concurrent execution for performance

This tour showcases the power of combining OpenAI's language models with Restate's durability guarantees for building production-ready agent systems.