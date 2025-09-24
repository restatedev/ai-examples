import datetime
import logging
import os

from openai import OpenAI
from anthropic import Anthropic

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def llm_call(prompt: str, system: str = "") -> str:
    """
    Calls the model with the given prompt and returns the response.

    Args:
        prompt (str): The user prompt to send to the model.
        system (str, optional): The system prompt to send to the model. Defaults to "".

    Returns:
        str: The response from the language model.
    """

    if os.getenv("OPENAI_API_KEY"):
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ]
        client = OpenAI()
        response = client.chat.completions.create(
            model="gpt-4o",
            max_tokens=4096,
            messages=messages,
            temperature=0.1,
        )
        return response.choices[0].message.content
    elif os.getenv("ANTHROPIC_API_KEY"):
        client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        messages = [{"role": "user", "content": prompt}]
        response = client.messages.create(
            model="claude-3-5-sonnet-latest",
            max_tokens=4096,
            system=system,
            messages=messages,
            temperature=0.1,
        )
        return response.content[0].text
    else:
        raise RuntimeError(
            "Missing API key: set either the env var OPENAI_API_KEY or ANTHROPIC_API_KEY"
        )


def print_evaluation(iteration: int, solution: str, evaluation: str):
    print(f"Iteration {iteration + 1}:")
    print(f"Solution: {solution[:100]}...")
    print(f"Evaluation: {evaluation}")
    print("-" * 50)


# MOCK DATA


def fetch_service_status():
    # Mock service status data (would be real API calls to monitoring systems)
    return {
        "api": {
            "name": "API Gateway",
            "status": "operational",
            "uptime_24h": 99.8,
            "response_time_avg": "120ms",
            "incidents": 0,
        },
        "database": {
            "name": "Primary Database",
            "status": "operational",
            "uptime_24h": 100.0,
            "response_time_avg": "15ms",
            "incidents": 0,
        },
        "payment": {
            "name": "Payment Service",
            "status": "degraded",
            "uptime_24h": 95.2,
            "response_time_avg": "450ms",
            "incidents": 1,
            "incident_description": "Intermittent timeout issues with payment processor",
        },
        "dashboard": {
            "name": "User Dashboard",
            "status": "operational",
            "uptime_24h": 99.9,
            "response_time_avg": "200ms",
            "incidents": 0,
        },
        "notifications": {
            "name": "Email/SMS Service",
            "status": "maintenance",
            "uptime_24h": 98.5,
            "response_time_avg": "N/A",
            "incidents": 0,
            "incident_description": "Scheduled maintenance until 14:00 UTC",
        },
    }


def create_support_ticket(request: str, user_id: str) -> dict:
    # Mock ticket creation (would be real API calls to ticketing systems)
    ticket_id = "TICKET-" + str(abs(hash(request)) % 10000)
    return {
        "ticket_id": ticket_id,
        "user_id": user_id,
        "status": "open",
        "created_at": datetime.datetime.now().isoformat(),
        "details": request,
    }


# Mock user database with subscription and usage data
users_db = {
    "user_12345": {
        "user_id": "user_12345",
        "email": "john@example.com",
        "subscription": {
            "plan": "Pro",
            "status": "active",
            "billing_cycle": "monthly",
            "price": 49.99,
            "next_billing": "2024-02-15",
        },
        "usage": {
            "api_calls_this_month": 10000,
            "api_limit": 10000,
            "storage_used_gb": 12.5,
            "storage_limit_gb": 50,
        },
        "account_status": "good_standing",
        "created_date": "2023-06-15",
    },
    "user_67890": {
        "user_id": "user_67890",
        "email": "jane@startup.com",
        "subscription": {
            "plan": "Enterprise",
            "status": "active",
            "billing_cycle": "yearly",
            "price": 999.99,
            "next_billing": "2024-06-01",
        },
        "usage": {
            "api_calls_this_month": 45000,
            "api_limit": 100000,
            "storage_used_gb": 180.2,
            "storage_limit_gb": 1000,
        },
        "account_status": "good_standing",
        "created_date": "2022-01-10",
    },
}


def query_user_database(user_id: str) -> dict | None:
    return users_db.get(user_id, None)


def parse_instructions(task_breakdown: str) -> dict:
    worker_instructions = {}
    for line in task_breakdown.strip().split("\n"):
        if ":" in line:
            task_type, instruction = line.split(":", 1)
            worker_instructions[task_type.strip()] = instruction.strip()

    # print the parsed instructions for debugging
    print(
        f"Orchestrator broke down text analysis into {len(worker_instructions)} specialized tasks:"
    )
    for task, instruction in worker_instructions.items():
        print(f"- {task}: {instruction}")

    return worker_instructions
