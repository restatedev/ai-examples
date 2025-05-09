import pydantic
import restate

from a_orchestrating_llm_calls.util.util import llm_call, extract_xml

"""
Evaluator-optimizer pattern with Restate

This example demonstrates how to use Restate to implement a loop of LLM calls, 
in which the first LLM generates a solution, and the second LLM evaluates that solution.
This loop is repeated until the solution meets the requirements.
Restate persists the outcomes of each of the LLM calls and if this loop runs for a long time,
and then fails, it will recover all the progress that was made until then.

This example is a translation of the Anthropic AI agents Python notebook examples:
https://github.com/anthropics/anthropic-cookbook/blob/main/patterns/agents/
"""

evaluator_optimizer = restate.Service("EvaluatorOptimizer")


class LoopRequest(pydantic.BaseModel):
    task: str
    evaluator_prompt: str
    generator_prompt: str


@evaluator_optimizer.handler()
async def loop(ctx: restate.Context, req: LoopRequest) -> tuple[str, list[dict]]:
    """Keep generating and evaluating until requirements are met."""
    memory = []
    chain_of_thought = []

    thoughts, result = await generate(ctx, req.generator_prompt, req.task)
    memory.append(result)
    chain_of_thought.append({"thoughts": thoughts, "result": result})

    while True:
        evaluation, feedback = await evaluate(
            ctx, req.evaluator_prompt, result, req.task
        )
        if evaluation == "PASS":
            return result, chain_of_thought

        llm_context = "\n".join(
            [
                "Previous attempts:",
                *[f"- {m}" for m in memory],
                f"\nFeedback: {feedback}",
            ]
        )

        thoughts, result = await generate(
            ctx, req.generator_prompt, req.task, llm_context
        )
        memory.append(result)
        chain_of_thought.append({"thoughts": thoughts, "result": result})


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
