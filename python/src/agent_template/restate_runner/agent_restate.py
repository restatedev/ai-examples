import json
import logging
from typing import Optional, Any, Callable, Awaitable, TypeVar, Type

import restate
from openai import OpenAI
from openai.lib._pydantic import to_strict_json_schema
from openai.types.responses import ResponseFunctionToolCall, Response, ResponseOutputMessage
from pydantic import BaseModel, ConfigDict
from restate.serde import PydanticJsonSerde

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


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

class Empty(BaseModel):
    model_config = ConfigDict(extra="forbid")

class Tool(BaseModel):
    name: str
    handler: Callable[[Any, I], Awaitable[O]]
    description: str
    input_type: Type[I]

    def to_tool_schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "name": format_name(self.name),
            "description": self.description,
            "parameters": to_strict_json_schema(self.input_type),
            "strict": True
        }


class Agent(BaseModel):
    name: str
    handoff_description: str
    instructions: str
    tools: list[Tool]
    handoffs: list[str] # agent names

    def to_tool_schema(self) -> dict[str, Any]:
        return {
        "type": "function",
        "name": f"{format_name(self.name)}",
        "description": self.handoff_description,
        "parameters": to_strict_json_schema(Empty),
        "strict": True
    }


def format_name(name: str) -> str:
    return name.replace(" ", "_").lower()

class ChatResponse(BaseModel):
    agent: Optional[str]
    messages: list[dict[str, Any]]

client = OpenAI()


async def run(
        ctx: restate.ObjectContext,
        starting_agent: Agent,
        agents: list[Agent],
        message: str) -> ChatResponse:

    current_agent_name: str = await ctx.get("current_agent_name") or format_name(starting_agent.name)
    ctx.set("current_agent_name", current_agent_name)
    logger.info(f"Running chat workflow for: {current_agent_name}")

    agents_dict = {format_name(agent.name): agent for agent in agents}
    agent = agents_dict[current_agent_name]
    logger.info(f"Agent at disposal: {agents_dict}")

    input_items = await ctx.get("input_items") or []
    input_items.append({"content": message, "role": "user"})
    logger.info(f"Current input items: {input_items}")

    while True:

        tools = {format_name(tool.name): tool for tool in agent.tools}
        tool_and_handoff_schemas = {format_name(tool.name): tool.to_tool_schema() for tool in agent.tools}
        tool_and_handoff_schemas.update({format_name(agent_name): agents_dict[format_name(agent_name)].to_tool_schema() for agent_name in agent.handoffs})
        print("Tools and handoffs:", tool_and_handoff_schemas)

        response = await ctx.run("Call LLM", lambda: client.responses.create(
                model="gpt-4o",
                instructions=agent.instructions,
                input=input_items,
                tools=tool_and_handoff_schemas.values(),
                stream=False
            ), serde=PydanticJsonSerde(Response))

        input_items.extend([{"role": "system", "content": item.model_dump_json()} for item in response.output])
        ctx.set("input_items", input_items)

        # TODO this is a list; handle the other output items
        command = response.output[0]
        print(f"{agent.name}:", command)

        # === 2. handle tool calls ===
        if isinstance(command, ResponseFunctionToolCall):
            # Handoffs
            if command.name in agents_dict.keys():
                agent = agents_dict[command.name]
                result = f"Transfered to {agent.name}."
            # Execute handler tool
            else:
                result = await execute_tool_call(ctx, command, tools)

            input_items.append({
                "role": "system",
                "content": result,
            })
            ctx.set("input_items", input_items)
        if isinstance(command, ResponseOutputMessage):
            break

    ctx.set("input_items", input_items)
    ctx.set("current_agent_name", format_name(agent.name))

    return ChatResponse(agent=agent.name, messages=input_items)


async def execute_tool_call(ctx: restate.ObjectContext,
                      command_message: ResponseFunctionToolCall,
                      tools: dict[str, Tool]):

    tool_to_call = tools[command_message.name]

    print("Calling tool:", tool_to_call.name)

    result = await ctx.service_call(tool_to_call.handler, arg=tool_to_call.input_type(**json.loads(command_message.arguments)))
    print("Tool result:", result)
    return result