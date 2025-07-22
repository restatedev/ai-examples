import pydantic
import restate

from util.util import llm_call, extract_xml

"""
Human-in-the-loop workflows with Restate

This example demonstrates how to use Restate to implement a feedback loop between a human operator and the LLM.
The human operator sends a request, the LLM responds with the solution. 
The same human operator (option 1 `run`) or another human operator (option 2 `run_with_promise`) can then give feedback, which triggers another LLM-based optimization step, and so on. 

This is implemented with a stateful entity called Virtual Object which keeps track of the memory and the chain of thought.
If the human answers one week or one month later, the session can be recovered and resumed. 

This example is a next iteration of the Anthropic AI agents Python notebook examples:
https://github.com/anthropics/anthropic-cookbook/blob/main/patterns/agents/
"""

human_in_the_loop_svc = restate.VirtualObject("HumanInTheLoopService")


@human_in_the_loop_svc.handler()
async def run_with_promise(
    ctx: restate.ObjectContext, task: str
) -> tuple[str, list[dict]]:
    """
    OPTION 1: Human evaluator gives feedback via a promise.
    This is a useful pattern when the original person requesting the task is not the one giving feedback.
    """

    # Generate the initial solution
    result = await generate(ctx, task)

    # Store the result in memory
    memory = await ctx.get("memory") or []
    memory.append(result)
    ctx.set("memory", memory)

    while True:
        # Durable promise that waits for human feedback
        id, feedback_promise = ctx.awakeable()
        await ctx.run("ask human feedback", lambda: ask_for_feedback(id))
        human_feedback = await feedback_promise

        # Check if the human feedback is a PASS
        if human_feedback == "PASS":
            return result, memory

        result = await generate(ctx, task, memory, human_feedback)
        memory.append(result)
        ctx.set("memory", memory)


@human_in_the_loop_svc.handler()
async def run(ctx: restate.ObjectContext, task: str) -> str:
    """
    OPTION 2: Human evaluator gives feedback by sending a new request to the same stateful session.
    This is a useful pattern when the original person requesting the task is also the one giving feedback.
    """

    memory = await ctx.get("memory") or []
    result = await generate(ctx, task, memory)
    memory.append(result)
    ctx.set("memory", memory)

    return result


# UTILS


async def generate(
    ctx: restate.Context, task: str, memory: str = "", human_feedback: str = ""
) -> str:
    """Generate and improve a solution based on feedback."""
    llm_context = "\n".join(
        [
            "Previous attempts:",
            *[f"- {m}" for m in memory],
            f"\nFeedback: {human_feedback}",
        ]
    )
    full_prompt = f"{llm_context}\nTask: {task}" if llm_context else f"Task: {task}"
    result = await ctx.run("LLM call", lambda: llm_call(full_prompt))

    print("\n=== GENERATION START ===")
    print(f"Generated:\n{result}")
    print("=== GENERATION END ===\n")

    return result


def ask_for_feedback(id):
    print("\n=== HUMAN FEEDBACK REQUIRED ===")
    print("Answer 'PASS' to accept the solution.")
    print("\n Send feedback via:")
    print(
        "\n curl http://localhost:8080/restate/awakeables/"
        + id
        + "/resolve --json '\"Your feedback...\"'"
    )

    # This is a placeholder for the actual feedback mechanism: maybe an email or chat message
