import json
import pickle
import typing

import restate
from restate.serde import Serde
from agents import RunResult, RunHooks, RunConfig, TResponseInputItem, TContext, ItemHelpers, MessageOutputItem, \
    HandoffOutputItem, ToolCallItem, ToolCallOutputItem, RunContextWrapper
from pydantic import BaseModel

from src.openaiagents.agents_runtime import my_agents
from src.openaiagents.agents_runtime.my_agents import EnrichedContext
from src.openaiagents.agents_runtime.restate_runner.restate_agent_runner import RestateRunner

agent_runner = restate.VirtualObject("AgentRunner")


class RunOpts(typing.TypedDict):
    custom_context: TContext | None
    input: str | list[TResponseInputItem]
    max_turns: int
    hooks: RunHooks[TContext] | None
    run_config: RunConfig | None


class RunOptsSerde(Serde[RunOpts]):
    def serialize(self, obj: typing.Optional[RunOpts]) -> bytes:
        return pickle.dumps(obj)

    def deserialize(self, buf: bytes) -> RunOpts:
        return pickle.loads(buf)

@agent_runner.handler(input_serde=RunOptsSerde())
async def execute_agent_call(ctx: restate.ObjectContext, args: RunOpts) -> str:
    # Retrieve the current agent of this session
    current_agent_name = await ctx.get("current_agent_name")
    if current_agent_name is None:
        current_agent_name = my_agents.triage_agent.name
        ctx.set("current_agent_name", current_agent_name)
    current_agent = my_agents.AGENTS[current_agent_name]

    input_items = await ctx.get("input_items") or []
    if isinstance(args["input"], str):
        input_items.append({"content": args["input"], "role": "user"})
    else:
        input_items.extend(args["input"])

    result: RunResult = await RestateRunner.run(
        current_agent,
        args["input"],
        context=EnrichedContext(context=args.get("custom_context", None),restate_context=ctx),
        max_turns=10,
        hooks=args.get("hooks", None),
        run_config=args.get("run_config", None))
    input_items = result.to_input_list()
    ctx.set("input_items", input_items)
    ctx.set("current_agent_name", result.last_agent.name)
    return prettify_response(result)


def prettify_response(result: RunResult):
    response = ""
    for new_item in result.new_items:
        agent_name = new_item.agent.name
        if isinstance(new_item, MessageOutputItem):
            print(f"{agent_name}: {ItemHelpers.text_message_output(new_item)}")
            response += f"{agent_name}: {ItemHelpers.text_message_output(new_item)}\n"
        elif isinstance(new_item, HandoffOutputItem):
            print(
                f"Handed off from {new_item.source_agent.name} to {new_item.target_agent.name}"
            )
            response += f"Handed off from {new_item.source_agent.name} to {new_item.target_agent.name}\n"
        elif isinstance(new_item, ToolCallItem):
            print(f"{agent_name}: Calling a tool")
            response += f"{agent_name}: Calling a tool\n"
        elif isinstance(new_item, ToolCallOutputItem):
            print(f"{agent_name}: Tool call output: {new_item.output}")
            response += f"{agent_name}: Tool call output: {new_item.output}"
        else:
            print(f"{agent_name}: Skipping item: {new_item.__class__.__name__}")
            response += f"{agent_name}: Skipping item: {new_item.__class__.__name__}\n"
    return response


