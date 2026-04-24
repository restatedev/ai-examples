"""
Interrupt & Regenerate

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
from datetime import timedelta

import restate
from pydantic import BaseModel
from restate import RestateDurableFuture, RunOptions, TerminalError

from util.litellm_call import llm_call


class ChatMessage(BaseModel):
    content: str = "Build me a small todo CLI in Python."


class TaskInput(BaseModel):
    agent_id: str
    messages: list[dict]


TASK_PROMPT = (
    "Take the user's latest request and respond with a full answer: "
    "first outline a high-level plan, then write a draft implementation, "
    "then polish it into a final version."
)


# ORCHESTRATOR VIRTUAL OBJECT
agent = restate.VirtualObject("CodingAgent")


# <start_message_handler>
@agent.handler()
async def message(ctx: restate.ObjectContext, msg: ChatMessage) -> None:
    """Receive a user message. A new message interrupts any ongoing task."""

    # (1) Access state of the Virtual Object
    messages = await ctx.get("messages", type_hint=list[dict]) or []
    messages.append({"role": "user", "content": msg.content})

    # (2) Interrupt the ongoing task and wait for its cleanup to finish.
    # The cancelled invocation finishes with a TerminalError; swallow it.
    current_task_id = await ctx.get("current_task_id", type_hint=str)
    if current_task_id:
        ctx.cancel_invocation(current_task_id)
        done: RestateDurableFuture[None] = ctx.attach_invocation(current_task_id)
        try:
            await restate.select(done=done, timed_out=ctx.sleep(timedelta(seconds=30)))
        except TerminalError:
            pass

    # (3) Start executing the new task
    handle = ctx.service_send(
        run_task, arg=TaskInput(agent_id=ctx.key(), messages=messages)
    )

    # (4) Store the handle to the task and persist the updated history
    invocation_id = await handle.invocation_id()
    ctx.set("current_task_id", invocation_id)
    ctx.set("messages", messages)
# <end_message_handler>


@agent.handler()
async def append_message(ctx: restate.ObjectContext, msg: ChatMessage) -> None:
    """Callback used by CodingTask.run_task to stream progress back into history."""
    messages = await ctx.get("messages", type_hint=list[dict]) or []
    messages.append({"role": "assistant", "content": msg.content})
    ctx.set("messages", messages)
    ctx.clear("current_task_id")


@agent.handler(kind="shared")
async def get_history(ctx: restate.ObjectSharedContext) -> list[dict]:
    return await ctx.get("messages", type_hint=list[dict]) or []


# LONG-RUNNING TASK SERVICE
task_service = restate.Service("CodingTask")


# <start_run_task>
@task_service.handler()
async def run_task(ctx: restate.Context, inp: TaskInput) -> None:
    """Long-running coding task. If interrupted, the cancellation surfaces
    as TerminalError at the next Restate await — we catch it, run durable
    cleanup, and re-raise so Restate records the invocation as cancelled."""
    try:
        result = await ctx.run_typed(
            "LLM call",
            llm_call,
            RunOptions(max_attempts=3),
            messages=inp.messages + [{"role": "user", "content": TASK_PROMPT}],
        )
        ctx.object_send(
            append_message,
            key=inp.agent_id,
            arg=ChatMessage(content=result.content or ""),
        )
    except TerminalError as err:
        # Cancellations surface as TerminalError with status_code == 409.
        content = (
            "[task cleanup ran after cancellation]"
            if err.status_code == 409
            else "[task cleanup ran after error]"
        )
        ctx.object_send(
            append_message,
            key=inp.agent_id,
            arg=ChatMessage(content=content),
        )
        raise
# <end_run_task>
