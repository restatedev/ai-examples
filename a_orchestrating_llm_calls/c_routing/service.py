from typing import Dict

import restate
from pydantic import BaseModel
from a_orchestrating_llm_calls.util.util import llm_call, extract_xml

"""
Routing with Restate

This example demonstrates how to use Restate to make and act on routing decisions.
Restate persists the decision and the request to the next tool/agent and makes sure it runs to completion exactly-once. 

This example is a translation of the Anthropic AI agents Python notebook examples:
https://github.com/anthropics/anthropic-cookbook/blob/main/patterns/agents/
"""

routing_svc = restate.Service("RoutingService")


class RouteRequest(BaseModel):
    input: str
    routes: dict[str, str]


@routing_svc.handler()
async def route(ctx: restate.Context, req: RouteRequest) -> str:
    """Route input to specialized prompt using content classification."""
    # First determine appropriate route using LLM with chain-of-thought
    print(f"\nAvailable routes: {list(req.routes.keys())}")
    selector_prompt = f"""
    Analyze the input and select the most appropriate support team from these options: {list(req.routes.keys())}
    First explain your reasoning, then provide your selection in this XML format:

    <reasoning>
    Brief explanation of why this ticket should be routed to a specific team.
    Consider key terms, user intent, and urgency level.
    </reasoning>

    <selection>
    The chosen team name
    </selection>.

    Input: {req.input}""".strip()

    route_response = await ctx.run(
        "Determine routing", lambda: llm_call(selector_prompt)
    )
    reasoning = extract_xml(route_response, "reasoning")
    route_key = extract_xml(route_response, "selection").strip().lower()

    print("Routing Analysis:")
    print(reasoning)
    print(f"\nSelected route: {route_key}")

    # Option 1: Process input with selected specialized prompt
    selected_prompt = req.routes[route_key]
    return await ctx.run("Route", lambda: llm_call(f"{selected_prompt}\nInput: {req.input}"))

    # Option 2: In Restate, this could also be a call to run a tool (service handler)
    # Have a look at the more advanced examples in this repo to see how far you can go with this
    # service_name, task_name = req.routes[route_key].split("/")
    # task_response = await ctx.generic_call(service_name, task_name, req.input.encode())
