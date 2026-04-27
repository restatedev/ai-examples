"""Shared helpers and sub-agent services used across the tour-of-agents
LangChain examples.

The sub-agents below mirror the OpenAI-Agents tour: each is a stand-alone
Restate service that runs an LLM via `create_agent` + `RestateMiddleware`.
This keeps every LLM and tool call durable, while letting parent workflows
invoke sub-agents over Restate RPC."""

import restate
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from restate import TerminalError

from restate.ext.langchain import RestateMiddleware

from .models import InsuranceClaim, WeatherRequest, WeatherResponse


# ---------- weather ----------


async def fetch_weather(req: WeatherRequest) -> WeatherResponse:
    fail_on_denver(req.city)
    return WeatherResponse(temperature=23, description="Sunny")


def fail_on_denver(city: str) -> None:
    if city == "Denver":
        raise Exception("[👻 SIMULATED] Fetching weather failed: Weather API down...")


# ---------- human-in-the-loop ----------


async def request_human_review(claim: InsuranceClaim, awakeable_id: str) -> None:
    """Stand-in for sending the claim to a human reviewer."""
    print(f"🔔 Human review requested: {claim.model_dump_json()}")
    print(f"  Resolve via: \n")
    print(
        f"  curl localhost:8080/restate/awakeables/{awakeable_id}/resolve --json 'true'"
    )


# ---------- claim sub-tasks ----------


async def check_eligibility(claim: InsuranceClaim) -> str:
    return "eligible"


async def compare_to_standard_rates(claim: InsuranceClaim) -> str:
    return "reasonable"


async def check_fraud(claim: InsuranceClaim) -> str:
    return "low risk"


# ---------- payments ----------


async def convert_currency(amount: float, source: str, target: str) -> float:
    return amount


async def process_payment(claim_id: str, amount: float) -> str:
    return f"Payment processed for claim {claim_id}: ${amount}"


# ---------- sub-agents as Restate services ----------


def _run_specialist(system_prompt: str):
    """Build a one-shot LLM-only specialist agent."""
    return create_agent(
        model=init_chat_model("openai:gpt-5.4"),
        tools=[],
        system_prompt=system_prompt,
        middleware=[RestateMiddleware()],
    )


eligibility_agent_service = restate.Service("EligibilityAgent")


@eligibility_agent_service.handler()
async def run_eligibility_agent(_ctx: restate.Context, claim: InsuranceClaim) -> str:
    agent = _run_specialist(
        "Decide whether the following claim is eligible for reimbursement."
        " Respond with eligible if it's a medical claim, and not eligible otherwise."
    )
    result = await agent.ainvoke({"messages": [{"role": "user", "content": claim.model_dump_json()}]})
    return result["messages"][-1].content


rate_comparison_agent_service = restate.Service("RateComparisonAgent")


@rate_comparison_agent_service.handler()
async def run_rate_comparison_agent(_ctx: restate.Context, claim: InsuranceClaim) -> str:
    agent = _run_specialist(
        "Decide whether the cost of the claim is reasonable given the treatment."
        " Respond with reasonable or not reasonable."
    )
    result = await agent.ainvoke({"messages": [{"role": "user", "content": claim.model_dump_json()}]})
    return result["messages"][-1].content


fraud_agent_service = restate.Service("FraudAgent")


@fraud_agent_service.handler()
async def run_fraud_agent(_ctx: restate.Context, claim: InsuranceClaim) -> str:
    agent = _run_specialist(
        "Decide whether the claim is fraudulent."
        " Always respond with low risk, medium risk, or high risk."
    )
    result = await agent.ainvoke({"messages": [{"role": "user", "content": claim.model_dump_json()}]})
    return result["messages"][-1].content
