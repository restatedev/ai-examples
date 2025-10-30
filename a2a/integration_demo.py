#!/usr/bin/env python3
"""
Comprehensive demo of Restate + Google A2A SDK integration approaches.

This script demonstrates all three integration patterns:
1. Traditional Restate A2A implementation
2. Hybrid Google ADK + Restate approach
3. Pure Google A2A SDK implementation

Run with: python integration_demo.py --help
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path

import click
from dotenv import load_dotenv

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@click.group()
def cli():
    """Restate + Google A2A SDK Integration Demo"""
    pass


@cli.command()
@click.option('--port', default=9081, help='Port for traditional Restate server')
def traditional(port):
    """Run traditional Restate A2A implementation"""
    logger.info("🔧 Starting Traditional Restate A2A Implementation")
    logger.info("Features: Full durability, custom protocol, complex workflows")

    try:
        from a2a_samples.reimbursement.agent import ReimbursementAgent
        from a2a_samples.reimbursement.__main__ import main as reimbursement_main

        # This would start the traditional server
        logger.info(f"Traditional server would start on port {port}")
        logger.info("Implementation: a2a_samples.reimbursement")

    except ImportError as e:
        logger.error(f"Could not import traditional implementation: {e}")


@cli.command()
@click.option('--port', default=9082, help='Port for Google A2A SDK server')
def pure_a2a(port):
    """Run pure Google A2A SDK implementation"""
    logger.info("🚀 Starting Pure Google A2A SDK Implementation")
    logger.info("Features: Official protocol, standard integration, no durability")

    try:
        from a2a_samples.adk_expense_reimbursement.agent import ReimbursementAgent
        from a2a_samples.adk_expense_reimbursement.__main__ import main as adk_main

        logger.info(f"Pure A2A SDK server would start on port {port}")
        logger.info("Implementation: a2a_samples.adk_expense_reimbursement")

    except ImportError as e:
        logger.error(f"Could not import A2A SDK implementation: {e}")


@cli.command()
@click.option('--port', default=9083, help='Port for hybrid server')
@click.option('--mode', type=click.Choice(['traditional', 'hybrid', 'pure-a2a']),
              default='hybrid', help='Hybrid server mode')
def hybrid(port, mode):
    """Run hybrid Google ADK + Restate implementation"""
    logger.info("⚡ Starting Hybrid Google ADK + Restate Implementation")
    logger.info("Features: Official protocol + Full durability + Modern AI")

    try:
        from a2a_samples.hybrid_reimbursement.agent import HybridReimbursementAgent

        agent = HybridReimbursementAgent()

        if mode == 'traditional':
            middleware = agent.get_traditional_middleware()
            logger.info("Using traditional Restate middleware")
        elif mode == 'hybrid':
            middleware = agent.get_hybrid_middleware()
            logger.info("Using hybrid ADK + Restate middleware")
        elif mode == 'pure-a2a':
            app = agent.get_pure_a2a_app()
            logger.info("Using pure A2A SDK application")

        logger.info(f"Hybrid server would start on port {port} in {mode} mode")
        logger.info("Implementation: a2a_samples.hybrid_reimbursement")

    except ImportError as e:
        logger.error(f"Could not import hybrid implementation: {e}")


@cli.command()
def compare():
    """Compare all three integration approaches"""
    logger.info("📊 Integration Approach Comparison")

    comparison = {
        "Traditional Restate A2A": {
            "Protocol": "Custom JSON-RPC implementation",
            "Durability": "✅ Full Restate durability",
            "State Management": "✅ Persistent virtual objects",
            "Workflows": "✅ Complex workflows (approval, scheduling)",
            "Cancellation": "✅ Built-in cancellation support",
            "Type Safety": "⚠️ Custom type definitions",
            "Standards Compliance": "⚠️ Custom A2A implementation",
            "Agent Intelligence": "🔧 Custom agent logic",
            "Use Case": "Complex business processes requiring reliability"
        },

        "Pure Google A2A SDK": {
            "Protocol": "✅ Official A2A protocol implementation",
            "Durability": "❌ No built-in durability",
            "State Management": "❌ In-memory only",
            "Workflows": "❌ Simple request-response",
            "Cancellation": "⚠️ Application-level only",
            "Type Safety": "✅ Official SDK type definitions",
            "Standards Compliance": "✅ Full A2A protocol compliance",
            "Agent Intelligence": "✅ Google ADK capabilities",
            "Use Case": "Standard A2A ecosystem integration"
        },

        "Hybrid ADK + Restate": {
            "Protocol": "✅ Official A2A protocol via SDK",
            "Durability": "✅ Full Restate durability",
            "State Management": "✅ Persistent virtual objects",
            "Workflows": "✅ Complex workflows + AI intelligence",
            "Cancellation": "✅ Restate-based cancellation",
            "Type Safety": "✅ SDK types + validation adapters",
            "Standards Compliance": "✅ Official protocol compliance",
            "Agent Intelligence": "✅ Google ADK + custom workflows",
            "Use Case": "Best of both worlds - production ready"
        }
    }

    for approach, features in comparison.items():
        logger.info(f"\n🔍 {approach}")
        for feature, status in features.items():
            logger.info(f"  {feature}: {status}")


@cli.command()
@click.option('--approach', type=click.Choice(['traditional', 'pure-a2a', 'hybrid']),
              required=True, help='Which approach to test')
def test_request(approach):
    """Send a test request to demonstrate the integration"""

    test_message = "I need to reimburse $75 for client lunch on December 1st"

    logger.info(f"🧪 Testing {approach} approach with message: '{test_message}'")

    if approach == 'traditional':
        logger.info("Would send to: http://localhost:9081/restate/v1/ReimbursementAgentA2AServer/process_request")

    elif approach == 'pure-a2a':
        logger.info("Would send to: http://localhost:9082/")

    elif approach == 'hybrid':
        logger.info("Would send to: http://localhost:9083/restate/v1/HybridReimbursementAgentA2AServer/process_request")

    # Example request payload
    request_payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tasks/send",
        "params": {
            "id": f"test-task-{approach}",
            "message": {
                "role": "user",
                "parts": [{"type": "text", "text": test_message}]
            }
        }
    }

    logger.info("Request payload:")
    logger.info(json.dumps(request_payload, indent=2))


@cli.command()
def architecture():
    """Show the integration architecture"""
    logger.info("🏗️ Integration Architecture Overview")

    architecture_diagram = """

┌─────────────────────────────────────────────────────────────────────────────┐
│                           CLIENT APPLICATIONS                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │    Web UI   │  │   Mobile    │  │  CLI Tool   │  │  Other A2A  │        │
│  │             │  │     App     │  │             │  │   Agents    │        │
│  └─────┬───────┘  └─────┬───────┘  └─────┬───────┘  └─────┬───────┘        │
└────────┼──────────────────┼──────────────────┼──────────────────┼────────────┘
         │                  │                  │                  │
         │                  │                  │                  │
         │                  A2A Protocol (JSON-RPC)              │
         │                  │                  │                  │
┌────────▼──────────────────▼──────────────────▼──────────────────▼────────────┐
│                        INTEGRATION LAYER                                     │
│                                                                               │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐             │
│  │   Traditional   │  │   Pure A2A SDK  │  │  Hybrid ADK +   │             │
│  │   Restate A2A   │  │                 │  │   Restate       │             │
│  │  ┌───────────┐  │  │  ┌───────────┐  │  │  ┌───────────┐  │             │
│  │  │  Custom   │  │  │  │ Official  │  │  │  │ Official  │  │             │
│  │  │ Protocol  │  │  │  │ A2A SDK   │  │  │  │ A2A SDK   │  │             │
│  │  │ Handler   │  │  │  │ Protocol  │  │  │  │ Protocol  │  │             │
│  │  └─────┬─────┘  │  │  └─────┬─────┘  │  │  └─────┬─────┘  │             │
│  │        │        │  │        │        │  │        │        │             │
│  │  ┌─────▼─────┐  │  │  ┌─────▼─────┐  │  │  ┌─────▼─────┐  │             │
│  │  │  Custom   │  │  │  │ ADK Agent │  │  │  │ADK Bridge │  │             │
│  │  │   Agent   │  │  │  │           │  │  │  │           │  │             │
│  │  │   Logic   │  │  │  └───────────┘  │  │  └─────┬─────┘  │             │
│  │  └─────┬─────┘  │  │                 │  │        │        │             │
│  └────────┼────────┘  └─────────────────┘  │  ┌─────▼─────┐  │             │
│           │                                │  │  Restate  │  │             │
│           │                                │  │  Bridge   │  │             │
│           │                                │  └─────┬─────┘  │             │
│           │                                └────────┼────────┘             │
└───────────┼─────────────────────────────────────────┼──────────────────────┘
            │                                         │
            │                                         │
            │              RESTATE RUNTIME            │
            │                                         │
┌───────────▼─────────────────────────────────────────▼──────────────────────┐
│                                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐           │
│  │ Virtual Objects │  │ Durable Exec    │  │ State Storage   │           │
│  │ (Task Objects)  │  │ (Workflows)     │  │ (Persistence)   │           │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘           │
│                                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐           │
│  │   Cancellation  │  │   Scheduling    │  │   Retries &     │           │
│  │   Support       │  │   (Delayed)     │  │   Recovery      │           │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘           │
└─────────────────────────────────────────────────────────────────────────────┘

Key Integration Patterns:

1. 📚 Traditional: Full Restate power, custom A2A protocol
2. 🚀 Pure A2A SDK: Standard compliance, simple deployment
3. ⚡ Hybrid: Best of both worlds - official protocol + full durability

"""

    logger.info(architecture_diagram)


@cli.command()
def setup():
    """Show setup instructions for all approaches"""
    logger.info("⚙️ Setup Instructions")

    setup_instructions = """
Environment Setup:
------------------

1. Install Dependencies:
   pip install restate-sdk[serde] a2a-sdk google-adk google-genai litellm

2. Set Environment Variables:
   # Required: Choose one
   export OPENAI_API_KEY="your-openai-key"
   export GEMINI_API_KEY="your-gemini-key"
   export GOOGLE_GENAI_USE_VERTEXAI=TRUE

   # Optional
   export LITELLM_MODEL="gemini/gemini-2.0-flash-001"
   export RESTATE_HOST="http://localhost:8080"

3. Start Restate Runtime (for traditional & hybrid modes):
   npx @restatedev/restate-server

Running Each Approach:
---------------------

Traditional Restate A2A:
   cd a2a_samples/reimbursement
   python __main__.py

Pure Google A2A SDK:
   cd a2a_samples/adk_expense_reimbursement
   python __main__.py --port 9082

Hybrid ADK + Restate:
   cd a2a_samples/hybrid_reimbursement
   python __main__.py --mode hybrid --port 9083

Testing:
--------

# Get agent card
curl http://localhost:PORT/.well-known/agent.json

# Send reimbursement request
curl -X POST http://localhost:PORT/endpoint \\
  -H "Content-Type: application/json" \\
  -d '{"jsonrpc": "2.0", "id": 1, "method": "tasks/send", ...}'

"""

    logger.info(setup_instructions)


if __name__ == '__main__':
    cli()