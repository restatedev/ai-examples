import json
from typing import Optional, Any, Callable, Awaitable, TypeVar, Type

import restate
from openai import OpenAI
from openai.lib._pydantic import to_strict_json_schema
from openai.types.responses import ResponseFunctionToolCall, Response, ResponseOutputMessage
from pydantic import BaseModel
from restate.serde import PydanticJsonSerde

RECOMMENDED_PROMPT_PREFIX = (
    "# System context\n"
    "You are part of a multi-agent system called the Agents SDK, designed to make agent "
    "coordination and execution easy. Agents uses two primary abstraction: **Agents** and "
    "**Handoffs**. An agent encompasses instructions and tools and can hand off a "
    "conversation to another agent when appropriate. "
    "Handoffs are achieved by calling a handoff function, generally named "
    "`transfer_to_<agent_name>`. Transfers between agents are handled seamlessly in the background;"
    " do not mention or draw attention to these transfers in your conversation with the user.\n"
)

I = TypeVar('I')
O = TypeVar('O')

class Tool(BaseModel):
    name: str
    handler: Callable[[Any, I], Awaitable[O]]
    description: str
    input_type: Type[I]

class Agent(BaseModel):
    name: str
    handoff_description: str
    instructions: str
    tools: list[Tool] | None
    handoffs: list[str] | None # agent names

class ChatResponse(BaseModel):
    agent: Optional[str]
    messages: list[dict[str, Any]]


def tool_to_schema(tool: Tool) -> dict[str, Any]:
    return {
        "type": "function",
        "name": tool.name,
        "description": tool.description,
        "parameters": to_strict_json_schema(tool.input_type),
        "strict": True
    }

client = OpenAI()


async def run(
        ctx: restate.ObjectContext,
        starting_agent: Agent,
        agents: dict[str, Agent],
        message: str) -> ChatResponse:

    current_agent_name = await ctx.get("current_agent_name")
    if current_agent_name is None:
        current_agent_name = starting_agent.name
        ctx.set("current_agent_name", current_agent_name)
    agent = agents[current_agent_name]

    input_items = await ctx.get("input_items") or []
    input_items.append({"content": message, "role": "user"})

    while True:
        # turn python functions into tools and save a reverse map
        tool_schemas = [tool_to_schema(tool) for tool in agent.tools]
        tools = {tool.name: tool for tool in agent.tools}

        # === 1. get openai completion ===
        response = await ctx.run("Call LLM", lambda: client.responses.create(
                model="gpt-4o",
                instructions=agent.instructions,
                input=input_items,
                tools=tool_schemas,
                stream=False
            ), serde=PydanticJsonSerde(Response))

        input_items.extend([{"role": "system", "content": item.model_dump_json()} for item in response.output])
        ctx.set("input_items", input_items)

        # TODO this is a list; handle the other output items
        command = response.output[0]
        print(f"{agent.name}:", command)

        # === 2. handle tool calls ===
        if isinstance(command, ResponseFunctionToolCall):
            result = await execute_tool_call(ctx, command, tools)

            # if type(result) is Agent:
            #     agent = result
            #     result = (
            #         f"Transfered to {agent.name}."
            #     )

            input_items.append({
                "role": "system",
                "content": result,
            })
            ctx.set("input_items", input_items)
        if isinstance(command, ResponseOutputMessage):
            break

    ctx.set("input_items", input_items)
    ctx.set("current_agent_name", agent.name)

    return ChatResponse(agent=agent.name, messages=input_items)


async def execute_tool_call(ctx: restate.ObjectContext,
                      command_message: ResponseFunctionToolCall,
                      tools: dict[str, Tool]):

    tool_to_call = tools[command_message.name]

    print("Calling tool:", tool_to_call.name)

    result = await ctx.service_call(tool_to_call.handler, arg=tool_to_call.input_type(**json.loads(command_message.arguments)))
    print("Tool result:", result)
    return result