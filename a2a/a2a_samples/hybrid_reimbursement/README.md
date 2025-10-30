# Hybrid Reimbursement Agent

This is a demonstration of integrating Google's A2A SDK with Restate's durable execution capabilities.

## Overview

The hybrid reimbursement agent showcases three different integration approaches:

1. **Traditional Mode**: Uses your original Restate-based A2A implementation with custom protocol handling
2. **Hybrid Mode**: Combines Google ADK agents with Restate's durability and workflow capabilities
3. **Pure A2A Mode**: Uses Google's A2A SDK directly without Restate (loses durability features)

## Features

### Traditional Mode Benefits
- Full Restate durability (retries, state persistence, workflow recovery)
- Custom A2A protocol implementation
- Complex workflow support (approval processes, scheduled tasks)
- Cancellation and state management

### Hybrid Mode Benefits (Recommended)
- Official A2A protocol compliance via Google SDK
- Restate durability for agent execution
- Google ADK's advanced agent capabilities
- Type safety and standardization
- Workflow durability with modern agent intelligence

### Pure A2A Mode Benefits
- Standard A2A protocol compliance
- Direct integration with A2A ecosystem
- Simpler deployment (no Restate dependency)
- **Note**: Loses durability, state persistence, and complex workflow capabilities

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   A2A Client    │    │  Hybrid Agent    │    │ Restate Runtime │
│                 │    │                  │    │                 │
│ ┌─────────────┐ │    │ ┌──────────────┐ │    │ ┌─────────────┐ │
│ │A2A Protocol │◄┼────┼►│ Google ADK   │ │    │ │ Durable     │ │
│ │ (JSON-RPC)  │ │    │ │ Agent        │ │    │ │ Execution   │ │
│ └─────────────┘ │    │ └──────┬───────┘ │    │ └─────────────┘ │
│                 │    │        │         │    │                 │
│                 │    │ ┌──────▼───────┐ │    │ ┌─────────────┐ │
│                 │    │ │ Restate      │◄┼────┼►│ State       │ │
│                 │    │ │ Bridge       │ │    │ │ Storage     │ │
│                 │    │ └──────────────┘ │    │ └─────────────┘ │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Usage

### Running the Agent

```bash
# Hybrid mode (recommended)
cd a2a_samples/hybrid_reimbursement
python -m a2a_samples.hybrid_reimbursement --mode hybrid --port 9083

# Traditional mode
python -m a2a_samples.hybrid_reimbursement --mode traditional --port 9083

# Pure A2A mode
python -m a2a_samples.hybrid_reimbursement --mode pure-a2a --port 9083
```

### Environment Variables

```bash
# Required: Either OpenAI or Gemini API key
export OPENAI_API_KEY="your-openai-key"
# OR
export GEMINI_API_KEY="your-gemini-key"
# OR use Vertex AI
export GOOGLE_GENAI_USE_VERTEXAI=TRUE

# Optional: Customize LLM model
export LITELLM_MODEL="gemini/gemini-2.0-flash-001"

# Optional: Restate host (for external Restate)
export RESTATE_HOST="http://localhost:8080"
```

### Testing the Agent

```bash
# Get agent card
curl http://localhost:9083/.well-known/agent.json

# Send a reimbursement request
curl -X POST http://localhost:9083/restate/v1/HybridReimbursementAgentA2AServer/process_request \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tasks/send",
    "params": {
      "id": "task-123",
      "message": {
        "role": "user",
        "parts": [{"type": "text", "text": "I need to reimburse $75 for client lunch on December 1st"}]
      }
    }
  }'
```

## Integration Benefits

### Why Use This Hybrid Approach?

1. **Best of Both Worlds**: Combines Google's advanced agent capabilities with Restate's enterprise-grade durability
2. **Standards Compliance**: Uses official A2A protocol implementation
3. **Future Proof**: Automatically gets updates to Google's A2A SDK
4. **Workflow Power**: Maintains complex business process capabilities
5. **Type Safety**: Benefits from Google SDK's comprehensive type system
6. **Gradual Migration**: Can run all three modes side-by-side during transition

### When to Use Each Mode

- **Hybrid Mode**: Production deployments requiring both intelligence and reliability
- **Traditional Mode**: Existing Restate-based workflows that don't need ADK features
- **Pure A2A Mode**: Simple agents or A2A ecosystem integration without durability needs

## Development

The hybrid implementation demonstrates:

- Type adapters between Google A2A SDK and Restate models
- Durable execution wrappers for ADK agents
- Protocol bridging between JSON-RPC and SDK types
- Workflow preservation with modern agent capabilities

See the implementation files:
- `sdk_adapter.py` - Type conversion between SDK and Restate models
- `adk_restate_bridge.py` - ADK agent integration with Restate
- `hybrid_middleware.py` - Combined protocol and durability handling