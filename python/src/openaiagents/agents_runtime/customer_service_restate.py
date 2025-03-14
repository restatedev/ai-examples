from __future__ import annotations as _annotations

from typing import TypedDict

import restate

from pydantic import BaseModel
from my_agents import LookupRequest
from src.openaiagents.agents_runtime.my_agents import faq_agent

from src.openaiagents.agents_runtime.restate_runner.restate_agent_service import RunOpts, agent_runner, execute_agent_call
### CONTEXT

class CustomerContext(TypedDict):
    passenger_name: str | None = None
    confirmation_number: str | None = None
    seat_number: str | None = None
    flight_number: str | None = None

### TOOLS
faq_agent_svc = restate.Service(faq_agent.name)


@faq_agent_svc.handler()
async def faq_lookup_tool(ctx: restate.Context, question: LookupRequest) -> str:
    print(f"faq_lookup_tool: {question}")
    if "bag" in question.question or "baggage" in question.question:
        return (
            "You are allowed to bring one bag on the plane. "
            "It must be under 50 pounds and 22 inches x 14 inches x 9 inches."
        )
    return "I'm sorry, I don't know the answer to that question."


### RUN
class CustomerChatRequest(BaseModel):
    customer_id: str
    user_input: str


customer_service_session = restate.VirtualObject("CustomerServiceSession")

@customer_service_session.handler()
async def chat(ctx: restate.ObjectContext, req: CustomerChatRequest) -> str:

    # If this is the first time, then retrieve the CustomerContext from an external CRM system
    customer_context: CustomerContext = await ctx.get("customer_context")
    if customer_context is None:
        customer_context = await ctx.run(
            "Get customer context",
            lambda: retrieve_customer_from_crm(req.customer_id))
        ctx.set("customer_context", customer_context)

    return await ctx.service_call(execute_agent_call, arg=RunOpts(
        input=req.user_input,
        custom_context=customer_context
    ))


app = restate.app(services=[customer_service_session, faq_agent_svc, agent_runner])



# -------------- Stubs ----------------

def retrieve_customer_from_crm(customer_id):
    return CustomerContext(passenger_name="Alice", confirmation_number="123456", seat_number="12A", flight_number="FLT-123")

