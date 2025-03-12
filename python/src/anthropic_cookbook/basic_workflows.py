import uuid
import restate
from pydantic import BaseModel
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Callable
from util import llm_call, extract_xml


# Translating Anthropic AI agents Python notebook examples to full-fledged resilient Restate apps
# https://github.com/anthropics/anthropic-cookbook/blob/main/patterns/agents/basic_workflows.ipynb

basic_workflows = restate.Service("BasicWorkflows")


# ---------- Prompt-chaining without Restate ----------

def chain(input: str, prompts: List[str]) -> str:
    """Chain multiple LLM calls sequentially, passing results between steps."""
    result = input
    for i, prompt in enumerate(prompts, 1):
        print(f"\nStep {i}:")
        result = llm_call(f"{prompt}\nInput: {result}")
        print(result)
    return result


# ---------- Prompt-chaining with Restate ----------

class ChainRequest(BaseModel):
    input: str
    prompts: List[str]

@basic_workflows.handler()
async def chain_restate(ctx: restate.Context, req: ChainRequest) -> str:
    result = req.input
    for i, prompt in enumerate(req.prompts, 1):
        print(f"\nStep {i}:")
        result = await ctx.run(
            f"LLM call ${i}",
            lambda: llm_call(f"{prompt}\nInput: {result}")
        )
        print(result)
    return result


# ---------- Parallelization without Restate ----------

def parallel(prompt: str, inputs: List[str], n_workers: int = 3) -> List[str]:
    """Process multiple inputs concurrently with the same prompt."""
    with ThreadPoolExecutor(max_workers=n_workers) as executor:
        futures = [executor.submit(llm_call, f"{prompt}\nInput: {x}") for x in inputs]
        return [f.result() for f in futures]


# ---------- Parallelization with Restate ----------

class ParallelizationRequest(BaseModel):
    prompt: str
    inputs: List[str]

@basic_workflows.handler()
async def parallel_restate(ctx: restate.Context, req: ParallelizationRequest) -> List[str]:
    futures = []
    for i, input in enumerate(req.inputs):
        sub_future = ctx.run(
            f"LLM call ${i}",
            lambda: llm_call(f"{req.prompt}\nInput: {input}")
        )
        futures.append(sub_future)

    return [await future for future in futures]



# ---------- Routing without Restate ----------

def route(input: str, routes: Dict[str, str]) -> str:
    """Route input to specialized prompt using content classification."""
    # First determine appropriate route using LLM with chain-of-thought
    print(f"\nAvailable routes: {list(routes.keys())}")
    selector_prompt = f"""
    Analyze the input and select the most appropriate support team from these options: {list(routes.keys())}
    First explain your reasoning, then provide your selection in this XML format:

    <reasoning>
    Brief explanation of why this ticket should be routed to a specific team.
    Consider key terms, user intent, and urgency level.
    </reasoning>

    <selection>
    The chosen team name
    </selection>

    Input: {input}""".strip()

    route_response = llm_call(selector_prompt)
    reasoning = extract_xml(route_response, 'reasoning')
    route_key = extract_xml(route_response, 'selection').strip().lower()

    print("Routing Analysis:")
    print(reasoning)
    print(f"\nSelected route: {route_key}")

    # Process input with selected specialized prompt
    selected_prompt = routes[route_key]
    return llm_call(f"{selected_prompt}\nInput: {input}")


# ---------- Routing with Restate ----------

class RouteRequest(BaseModel):
    input: str
    routes: Dict[str, str]


@basic_workflows.handler()
async def route(ctx: Context, req: RouteRequest) -> str:
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
    </selection>

    Input: {req.input}""".strip()

    route_response = ctx.run("Determine routing", lambda: llm_call(selector_prompt))
    reasoning = extract_xml(route_response, 'reasoning')
    route_key = extract_xml(route_response, 'selection').strip().lower()

    print("Routing Analysis:")
    print(reasoning)
    print(f"\nSelected route: {route_key}")

    # Option 1: Process input with selected specialized prompt
    # selected_prompt = req.routes[route_key]
    # return await ctx.run("Route", lambda: llm_call(f"{selected_prompt}\nInput: {req.input}"))

    # Option 2: In Restate, this could also be a call to instantiate a specific agent type and run a task
    selected_agent, task_name = req.routes[route_key].split("/")
    session_uuid = await ctx.run("Create session", lambda: str(uuid.uuid4()))
    task_response = await ctx.generic_call(selected_agent, task_name, req.input.encode(), session_uuid)
    return task_response.decode("utf-8")


app = restate.app(services=[basic_workflows])
