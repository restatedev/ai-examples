import restate
from google.adk.agents.llm_agent import Agent
from google.genai import types as genai_types
from pydantic import BaseModel

from app.utils.models import InsuranceClaim
from middleware.middleware import durable_model_calls
from middleware.restate_runner import RestateRunner
from middleware.restate_session_service import RestateSessionService

APP_NAME = "agents"

agent_service = restate.VirtualObject("MultiAgentClaimApproval")


@agent_service.handler()
async def run(ctx: restate.ObjectContext, claim: InsuranceClaim) -> str:
    user_id = "user"

    # Determine which specialist to use based on claim type
    review_agent = Agent(
        model=durable_model_calls(ctx, 'gemini-2.5-flash'),
        name='medical_specialist',
        description="Reviews medical insurance claims for coverage and necessity.",
        instruction="You are a medical specialist. Review medical claims for coverage and necessity. You can approve/deny claims up to $50,000. Make a final decision on this claim.",
    )

    car_agent = Agent(
        model=durable_model_calls(ctx, 'gemini-2.5-flash'),
        name='auto_specialist',
        description="Assesses auto insurance claims for liability and damage.",
        instruction="You are an auto specialist. Assess auto claims for liability and damage. You can approve/deny claims up to $25,000. Make a final decision on this claim.",
    )

    property_agent = Agent(
        model=durable_model_calls(ctx, 'gemini-2.5-flash'),
        name='property_specialist',
        description="Evaluates property insurance claims for damage and coverage.",
        instruction="You are a property specialist. Evaluate property claims for damage and coverage. Make a final decision on this claim.",
    )

    agent = Agent(
        model=durable_model_calls(ctx, 'gemini-2.5-flash'),
        name='intake_agent',
        description="Routes insurance claims to appropriate specialists.",
        instruction=f"You are an intake agent. Analyze this claim and determine if it should go to: medical specialist (for medical claims), auto specialist (for auto claims), or property specialist (for property claims). Based on the claim category '{claim.category}', route accordingly.",
        sub_agents=[property_agent, car_agent, review_agent]
    )


    session_service = RestateSessionService(ctx)
    await session_service.create_session(
        app_name=APP_NAME, user_id=user_id, session_id=ctx.key()
    )

    runner = RestateRunner(restate_context=ctx, agent=agent, app_name=APP_NAME, session_service=session_service)

    events = runner.run_async(
        user_id=user_id,
        session_id=ctx.key(),
        new_message=genai_types.Content(
            role="user",
            parts=[genai_types.Part.from_text(text=f"Claim: {claim.model_dump_json()}")]
        )
    )

    final_response = ""
    async for event in events:
        if event.is_final_response() and event.content and event.content.parts:
            final_response = event.content.parts[0].text

    return final_response
