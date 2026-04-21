"""
Abort & Regenerate

Interruptions are messages sent to the agent while it is already working.
For coding agents, this is critical: a task can take a while, and you may
see the agent going off in the wrong direction and want to add missing
context to get it back on track.

Restate lets us express interruptions using cancellation signals. Cancelling
an invocation raises a TerminalError at the next Restate await inside the
target handler. The error propagates through sub-invocations, giving us
stack-unwinding semantics across a distributed call tree, and leaves room
for durable cleanup (notifying the orchestrator, releasing resources, etc.).
"""

import restate
from pydantic import BaseModel
from restate import RunOptions, TerminalError

from util.litellm_call import llm_call


class UserMessage(BaseModel):
    content: str = "Build me a small todo CLI in Python."


class AssistantMessage(BaseModel):
    content: str
    final: bool = False


class TaskInput(BaseModel):
    agent_id: str
    messages: list[dict]


# <start_here>
# ORCHESTRATOR VIRTUAL OBJECT
agent = restate.VirtualObject("CodingAgent")


@agent.handler()
async def message(ctx: restate.ObjectContext, msg: UserMessage) -> None:
    """Receive a user message. A new message interrupts any ongoing task."""

    # (1) Access state of the Virtual Object
    messages = await ctx.get("messages", type_hint=list[dict]) or []
    messages.append({"role": "user", "content": msg.content})

    # (2) Interrupt the ongoing task
    current_task_id = await ctx.get("current_task_id", type_hint=str)
    if current_task_id:
        ctx.cancel_invocation(current_task_id)

    # (3) Start executing the new task
    handle = ctx.service_send(
        run_task, arg=TaskInput(agent_id=ctx.key(), messages=messages)
    )

    # (4) Store the handle to the task and persist the updated history
    invocation_id = await handle.invocation_id()
    ctx.set("current_task_id", invocation_id)
    ctx.set("messages", messages)


@agent.handler()
async def append_message(ctx: restate.ObjectContext, msg: AssistantMessage) -> None:
    """Callback used by CodingTask.run_task to stream progress back into history."""
    messages = await ctx.get("messages", type_hint=list[dict]) or []
    messages.append({"role": "assistant", "content": msg.content})
    ctx.set("messages", messages)
    if msg.final:
        ctx.clear("current_task_id")


@agent.handler(kind="shared")
async def get_history(ctx: restate.ObjectSharedContext) -> list[dict]:
    return await ctx.get("messages", type_hint=list[dict]) or []


# LONG-RUNNING TASK SERVICE
task_service = restate.Service("CodingTask")


@task_service.handler()
async def run_task(ctx: restate.Context, inp: TaskInput) -> None:
    """Multi-step coding task. If interrupted, surfaces as TerminalError
    at the next Restate await — we catch it, run cleanup, and re-raise."""

    steps = [
        ("plan", "Outline a high-level design for the user's latest request."),
        ("draft", "Write a first implementation based on the plan."),
        ("polish", "Refine and clean up the draft."),
    ]

    conversation = list(inp.messages)
    try:
        for i, (label, prompt) in enumerate(steps):
            result = await ctx.run_typed(
                f"LLM: {label}",
                llm_call,
                RunOptions(max_attempts=3),
                messages=conversation + [{"role": "user", "content": prompt}],
            )
            content = result.content or ""
            conversation.append({"role": "assistant", "content": content})
            ctx.object_send(
                append_message,
                key=inp.agent_id,
                arg=AssistantMessage(content=content, final=i == len(steps) - 1),
            )
    except TerminalError as err:
        # Cancellations surface as TerminalError with status_code == 409.
        # Only run the cancellation-specific cleanup for those; let other
        # terminal errors propagate untouched.
        if err.status_code == 409:
            ctx.object_send(
                append_message,
                key=inp.agent_id,
                arg=AssistantMessage(content="[task cleanup ran after cancellation]"),
            )
        else:
            ctx.object_send(
                append_message,
                key=inp.agent_id,
                arg=AssistantMessage(content=f"[task cleanup ran after error]"),
            )
        raise


# <end_here>
