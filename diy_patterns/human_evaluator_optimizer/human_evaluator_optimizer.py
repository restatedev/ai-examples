import pydantic
import restate

from a_orchestrating_llm_calls.util.util import llm_call, extract_xml

"""
Human-based evaluator with LLM-based optimizer with Restate

This example demonstrates how to use Restate to implement a feedback loop between a human operator and the LLM.
The human operator sends a request, the LLM responds with the solution. 
The human operator can then give feedback, which triggers another LLM-based optimization step, and so on. 

This is implemented with a stateful entity called Virtual Object which keeps track of the memory and the chain of thought.
If the human answers one week or one month later, the session can be recovered and resumed. 

This example is a next iteration of the Anthropic AI agents Python notebook examples:
https://github.com/anthropics/anthropic-cookbook/blob/main/patterns/agents/
"""

human_evaluator_optimizer = restate.VirtualObject("HumanEvaluatorOptimizer")


class GenerateRequest(pydantic.BaseModel):
    task: str
    generator_prompt: str


@human_evaluator_optimizer.handler()
async def run(
    ctx: restate.ObjectContext, req: GenerateRequest
) -> tuple[str, list[dict]]:
    memory = await ctx.get("memory") or []
    chain_of_thought = await ctx.get("chain_of_thought") or []

    thoughts, result = await generate(ctx, req.generator_prompt, req.task)
    memory.append(result)
    ctx.set("memory", memory)
    chain_of_thought.append({"thoughts": thoughts, "result": result})
    ctx.set("chain_of_thought", chain_of_thought)

    # There are two options here.
    # 1. Let the human evaluator communicate the feedback via resolving a promise (see awakeables in docs.restate.dev)
    # name, promise = ctx.awakeable()
    # await ctx.run("ask for human feedback", lambda: ask_for_feedback(name))
    # feedback = await promise

    # 2. Or just end this handler execution and let the human respond via a new invocation
    return result, chain_of_thought


# UTILS


async def generate(
    ctx: restate.Context, prompt: str, task: str, llm_context: str = ""
) -> tuple[str, str]:
    """Generate and improve a solution based on feedback."""
    full_prompt = (
        f"{prompt}\n{llm_context}\nTask: {task}"
        if llm_context
        else f"{prompt}\nTask: {task}"
    )
    response = await ctx.run("LLM call", lambda: llm_call(full_prompt))
    thoughts = extract_xml(response, "thoughts")
    result = extract_xml(response, "response")

    print("\n=== GENERATION START ===")
    print(f"Thoughts:\n{thoughts}\n")
    print(f"Generated:\n{result}")
    print("=== GENERATION END ===\n")

    return thoughts, result


async def evaluate(
    ctx: restate.Context, prompt: str, content: str, task: str
) -> tuple[str, str]:
    """Evaluate if a solution meets requirements."""
    full_prompt = f"{prompt}\nOriginal task: {task}\nContent to evaluate: {content}"
    response = await ctx.run("LLM call", lambda: llm_call(full_prompt))
    evaluation = extract_xml(response, "evaluation")
    feedback = extract_xml(response, "feedback")

    print("=== EVALUATION START ===")
    print(f"Status: {evaluation}")
    print(f"Feedback: {feedback}")
    print("=== EVALUATION END ===\n")

    return evaluation, feedback
