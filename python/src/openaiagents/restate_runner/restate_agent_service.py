import typing

import restate
from agents import RunResult, RunHooks, RunConfig, TResponseInputItem, TContext, ItemHelpers, MessageOutputItem, \
    HandoffOutputItem, ToolCallItem, ToolCallOutputItem, Agent

from src.openaiagents.restate_runner.restate_agent_runner import RestateRunner
from src.openaiagents.restate_runner.restate_tool_router import TCustomContext, EnrichedContext

# TYPES

class RunOpts(typing.TypedDict):
    agents: typing.Dict[str, Agent]
    init_agent: Agent
    custom_context: TCustomContext | None
    input: str | list[TResponseInputItem]
    max_turns: int
    hooks: RunHooks[TContext] | None
    run_config: RunConfig | None

# RESTATE SERVICE

async def execute_agent_call(ctx: restate.ObjectContext, args: RunOpts) -> RunResult:
    # Retrieve the current agent of this session
    current_agent_name = await ctx.get("current_agent_name")
    if current_agent_name is None:
        current_agent_name = args["init_agent"].name
        ctx.set("current_agent_name", current_agent_name)
    current_agent = args["agents"][current_agent_name]

    input_items = await ctx.get("input_items") or []
    if isinstance(args["input"], str):
        input_items.append({"content": args["input"], "role": "user"})
    else:
        input_items.extend(args["input"])

    result: RunResult = await RestateRunner.run(
        current_agent,
        input_items,
        context=EnrichedContext(custom_context=args.get("custom_context", None),restate_context=ctx),
        max_turns=args.get("max_turns", 10),
        hooks=args.get("hooks", None),
        run_config=args.get("run_config", None))
    input_items = result.to_input_list()
    ctx.set("input_items", input_items)
    ctx.set("current_agent_name", result.last_agent.name)
    return result


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
            response += f"{agent_name}: Tool call output: {new_item.output}\n"
        else:
            print(f"{agent_name}: Skipping item: {new_item.__class__.__name__}")
            response += f"{agent_name}: Skipping item: {new_item.__class__.__name__}\n"
    return response


