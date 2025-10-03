import datetime

import httpx
from pydantic import BaseModel
from restate import TerminalError


def print_evaluation(iteration: int, solution: str, evaluation: str):
    print(f"Iteration {iteration + 1}:")
    print(f"Solution: {solution[:100]}...")
    print(f"Evaluation: {evaluation}")
    print("-" * 50)


# MOCK DATA


def fetch_service_status() -> str:
    # Mock service status data (would be real API calls to monitoring systems)
    return str(
        {
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
    )


class SupportTicket(BaseModel):
    user_id: str
    message: str


def create_support_ticket(ticket: SupportTicket) -> str:
    # Mock ticket creation (would be real API calls to ticketing systems)
    ticket_id = "TICKET-" + str(abs(hash(request)) % 10000)
    return str(
        {
            "ticket_id": ticket_id,
            "user_id": ticket.user_id,
            "status": "open",
            "created_at": datetime.datetime.now().isoformat(),
            "details": ticket.message,
        }
    )


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


def query_user_db(user_id: str) -> str:
    content = users_db.get(user_id, None)
    if content:
        return str(content)
    else:
        return "User not found"


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


class HumanReviewRequest(BaseModel):
    request: str


class Content(BaseModel):
    message: str = "Very explicit content that might violate the policy."


def notify_moderator(content: Content, approval_id: str):
    """Notify human moderator about content requiring review."""
    print("\n🔍 CONTENT MODERATION REQUIRED 🔍")
    print(f"Content: {content.message}")
    print(f"Awaiting human decision...")
    print("\nTo approve:")
    print(
        f"curl http://localhost:8080/restate/awakeables/{approval_id}/resolve --json '\"approved\"'"
    )
    print("\nTo reject:")
    print(
        f"curl http://localhost:8080/restate/awakeables/{approval_id}/resolve --json '\"rejected\"'"
    )


class WeatherRequest(BaseModel):
    city: str


async def get_weather(req: WeatherRequest) -> dict:
    # This is a simulated failure to demo Durable Execution retries.
    try:
        resp = httpx.get(
            f"https://wttr.in/{httpx.URL(req.city)}?format=j1", timeout=10.0
        )
        resp.raise_for_status()

        if resp.text.startswith("Unknown location"):
            raise TerminalError(
                f"Unknown location: {req.city}. Please provide a valid city name."
            )

        return resp.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise TerminalError(
                f"City not found: {req.city}. Please provide a valid city name."
            ) from e
        else:
            raise Exception(f"HTTP error occurred: {e}") from e
