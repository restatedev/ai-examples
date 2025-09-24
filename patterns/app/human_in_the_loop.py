import restate

from pydantic import BaseModel

from util import llm_call

"""
Human-in-the-loop workflows with Restate

This example demonstrates how to use Restate to implement a feedback loop between a human operator and the LLM.
The human operator sends a request, the LLM responds with the solution. 
The same human operator (option 1 `run`) or another human operator (option 2 `run_with_promise`) can then give feedback, which triggers another LLM-based optimization step, and so on. 

This is implemented with a stateful entity called Virtual Object which keeps track of the memory and the chain of thought.
If the human answers one week or one month later, the session can be recovered and resumed. 
"""

human_in_the_loop_svc = restate.VirtualObject("HumanInTheLoopService")

# Example input text to analyze
# Ask as feedback to make it funnier, or more technical, etc.
example_prompt = "Write a poem about Durable Execution"


class Prompt(BaseModel):
    message: str = example_prompt


@human_in_the_loop_svc.handler()
async def run_with_promise(ctx: restate.ObjectContext, prompt: Prompt) -> str:
    """
    Human evaluator gives feedback via a promise.
    This is a useful pattern when the original person requesting the task is not the one giving feedback.
    """

    # Generate the initial solution
    result = await generate(ctx, prompt)
    # Store the result in memory
    memory = [result]
    while True:
        # Durable promise that waits for human feedback
        id, feedback_promise = ctx.awakeable(type_hint=str)
        await ctx.run("ask human feedback", lambda: ask_for_feedback(id))
        human_feedback = await feedback_promise

        # Check if the human feedback is a PASS
        if human_feedback == "PASS":
            return (
                f"Final accepted solution:\n{result} \n\n Memory of attempts:\n"
                + "\n".join(memory)
            )

        result = await generate(ctx, prompt, memory, human_feedback)
        memory.append(result)


# UTILS
async def generate(
    ctx: restate.Context,
    prompt: Prompt,
    memory: list[str] = None,
    human_feedback: str = "",
) -> str:
    """Generate and improve a solution based on feedback."""
    llm_context = "\n".join(
        [
            "Previous attempts:",
            *[f"- {m}" for m in memory],
            f"\nFeedback: {human_feedback}",
        ]
    )
    full_prompt = f"{llm_context}\nTask: {prompt}" if llm_context else f"Task: {prompt}"
    result = await ctx.run("LLM call", lambda: llm_call(full_prompt))
    print(f"Generated:\n{result}")
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
