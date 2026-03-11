import restate
from google.adk import Agent, Runner
from google.adk.apps import App
from google.adk.events import Event
from google.genai.types import Content, Part
from restate.ext.adk import RestateSessionService, RestatePlugin
from typing import AsyncGenerator
from utils.models import (
    WeatherResponse,
    InsuranceClaim,
WeatherRequest
)

async def parse_agent_response(events: AsyncGenerator[Event, None]) -> str:
    """Run an ADK agent and return the final text response."""
    final_response = ""
    async for event in events:
        if event.is_final_response() and event.content and event.content.parts:
            if event.content.parts[0].text:
                final_response = event.content.parts[0].text
    return final_response


# <start_weather>
async def fetch_weather(req: WeatherRequest) -> WeatherResponse:
    fail_on_denver(req.city)
    return WeatherResponse(temperature=23, description="Sunny")

# <end_weather>


def fail_on_denver(city):
    if city == "Denver":
        raise Exception("[👻 SIMULATED] Fetching weather failed: Weather API down...")


async def request_review(claim: InsuranceClaim, awakeable_id: str) -> None:
    """Simulate requesting human review."""
    print(f"🔔 Human review requested for claim {claim.model_dump_json()}")
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
    # Simple fraud detection based on claim characteristics
    return "low risk"


APP_NAME = "agents"

eligibility_agent = Agent(
    model="gemini-2.5-flash",
    name="EligibilityAgent",
    description="Decide whether the following claim is eligible for reimbursement.",
    instruction="Respond with eligible if it's a medical claim, and not eligible otherwise.",
)

eligibility_app = App(
    name=APP_NAME, root_agent=eligibility_agent, plugins=[RestatePlugin()]
)
eligibility_runner = Runner(
    app=eligibility_app, session_service=RestateSessionService()
)

# <start_eligibility>
eligibility_agent_service = restate.VirtualObject("EligibilityAgent")


@eligibility_agent_service.handler()
async def run_eligibility_agent(
    ctx: restate.ObjectContext, claim: InsuranceClaim
) -> str:
    prompt = f"Claim: {claim.model_dump_json()}"
    events = eligibility_runner.run_async(
        user_id=ctx.key(),
        session_id=claim.session_id,
        new_message=Content(role="user", parts=[Part.from_text(text=prompt)]),
    )

    return await parse_agent_response(events)
# <end_eligibility>


rate_comparison_agent = Agent(
    model="gemini-2.5-flash",
    name="RateComparisonAgent",
    description="Decide whether the cost of the claim is reasonable given the treatment.",
    instruction="Respond with reasonable or not reasonable.",
)

rate_comparison_app = App(
    name=APP_NAME, root_agent=rate_comparison_agent, plugins=[RestatePlugin()]
)
rate_comparison_runner = Runner(
    app=rate_comparison_app, session_service=RestateSessionService()
)

rate_comparison_agent_service = restate.VirtualObject("RateComparisonAgent")


@rate_comparison_agent_service.handler()
async def run_rate_comparison_agent(
    ctx: restate.ObjectContext, claim: InsuranceClaim
) -> str:
    prompt = f"Claim: {claim.model_dump_json()}"
    events = rate_comparison_runner.run_async(
        user_id=ctx.key(),
        session_id=claim.session_id,
        new_message=Content(role="user", parts=[Part.from_text(text=prompt)]),
    )

    return await parse_agent_response(events)


fraud_agent = Agent(
    model="gemini-2.5-flash",
    name="FraudCheckAgent",
    description="Decide whether the claim is fraudulent.",
    instruction="Always respond with low risk, medium risk, or high risk.",
)

fraud_app = App(name=APP_NAME, root_agent=fraud_agent, plugins=[RestatePlugin()])
fraud_runner = Runner(app=fraud_app, session_service=RestateSessionService())

fraud_agent_service = restate.VirtualObject("FraudAgent")


@fraud_agent_service.handler()
async def run_fraud_agent(ctx: restate.ObjectContext, claim: InsuranceClaim) -> str:
    prompt = f"Claim: {claim.model_dump_json()}"
    events = fraud_runner.run_async(
        user_id=ctx.key(),
        session_id=claim.session_id,
        new_message=Content(role="user", parts=[Part.from_text(text=prompt)]),
    )

    return await parse_agent_response(events)


async def convert_currency(amount: float, source: str, target: str) -> float:
    """Convert currency (placeholder)."""
    return amount*1.3


async def process_payment(claim_id: str, amount: float) -> str:
    """Process payment (placeholder)."""
    return f"Payment processed for claim {claim_id}: ${amount}"