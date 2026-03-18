import restate
from pydantic_ai import Agent
from restate.ext.pydantic import RestateAgent

from utils.models import (
    WeatherResponse,
    InsuranceClaim,
    WeatherRequest,
)


# <start_weather>
async def fetch_weather(req: WeatherRequest) -> WeatherResponse:
    fail_on_denver(req.city)
    return WeatherResponse(temperature=23, description="Sunny")


# <end_weather>


def fail_on_denver(city):
    if city == "Denver":
        raise Exception("[SIMULATED] Fetching weather failed: Weather API down...")


async def request_human_review(claim: InsuranceClaim, awakeable_id: str) -> None:
    """Simulate requesting human review."""
    print(f"Human review requested: {claim.model_dump_json()}")
    print(f"  Submit your claim review via: \n ")
    print(
        f"  curl localhost:8080/restate/awakeables/{awakeable_id}/resolve --json 'true'"
    )


# Additional utility functions for parallel processing
async def check_eligibility(claim: InsuranceClaim) -> str:
    """Check claim eligibility (simplified version)."""
    return "eligible"


async def compare_to_standard_rates(claim: InsuranceClaim) -> str:
    """Compare claim to standard rates (simplified version)."""
    return "reasonable"


async def check_fraud(claim: InsuranceClaim) -> str:
    """Check for fraud indicators (simplified version)."""
    return "low risk"


# <start_eligibility>
eligibility_agent = Agent(
    "openai:gpt-4o-mini",
    system_prompt="Decide whether the following claim is eligible for reimbursement."
    "Respond with eligible if it's a medical claim, and not eligible otherwise.",
)
restate_eligibility_agent = RestateAgent(eligibility_agent)

eligibility_agent_service = restate.Service("EligibilityAgent")


@eligibility_agent_service.handler()
async def run_eligibility_agent(_ctx: restate.Context, claim: InsuranceClaim) -> str:
    result = await restate_eligibility_agent.run(claim.model_dump_json())
    return result.output


# <end_eligibility>


rate_comparison_agent = Agent(
    "openai:gpt-4o-mini",
    system_prompt="Decide whether the cost of the claim is reasonable given the treatment."
    "Respond with reasonable or not reasonable.",
)
restate_rate_comparison_agent = RestateAgent(rate_comparison_agent)

rate_comparison_agent_service = restate.Service("RateComparisonAgent")


@rate_comparison_agent_service.handler()
async def run_rate_comparison_agent(
    _ctx: restate.Context, claim: InsuranceClaim
) -> str:
    result = await restate_rate_comparison_agent.run(claim.model_dump_json())
    return result.output


fraud_agent = Agent(
    "openai:gpt-4o-mini",
    system_prompt="Decide whether the claim is fraudulent."
    "Always respond with low risk, medium risk, or high risk.",
)
restate_fraud_agent = RestateAgent(fraud_agent)

fraud_agent_service = restate.Service("FraudAgent")


@fraud_agent_service.handler()
async def run_fraud_agent(_ctx: restate.Context, claim: InsuranceClaim) -> str:
    result = await restate_fraud_agent.run(claim.model_dump_json())
    return result.output


async def convert_currency(amount: float, source: str, target: str) -> float:
    """Convert currency (placeholder)."""
    return amount


async def process_payment(claim_id: str, amount: float) -> str:
    """Process payment (placeholder)."""
    return f"Payment processed for claim {claim_id}: ${amount}"
