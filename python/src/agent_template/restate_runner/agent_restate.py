import json
import logging
import typing
from typing import Optional, Any, Callable, Awaitable, TypeVar, Type, Union

import restate
from openai import OpenAI
from openai.lib._pydantic import to_strict_json_schema
from openai.types.responses import ResponseFunctionToolCall, Response, ResponseOutputMessage
from pydantic import BaseModel, ConfigDict, Field
from restate import TerminalError
from restate.serde import PydanticJsonSerde
from typing_extensions import Generic

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

I = TypeVar('I', bound=BaseModel)
O = TypeVar('O', bound=BaseModel)

client = OpenAI()

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

ServiceType = typing.Literal["Service", "VirtualObject", "Workflow"]


class Empty(BaseModel):
    model_config = ConfigDict(extra="forbid")

# class GenericRestateTool(BaseModel, Generic[I,O]):
#     service_name: str
#     service_type: ServiceType
#     handler_name: str
#     input_type: Type[I]
#     output_type: Type[O]

class RestateTool(BaseModel):
    tool_call: Callable[[Any, I], Awaitable[O]]
    name: str = Field(default_factory=lambda data: getattr(data["tool_call"], '__name__', ''))
    description: str = Field(default_factory=lambda data: getattr(data["tool_call"], '__doc__', ''))
    input_type: Type[I] = Field(default_factory=lambda data: getattr(data["tool_call"], '__annotations__', {}).get('req'))
    output_type: Type[I] = Field(default_factory=lambda data: getattr(data["tool_call"], '__annotations__', {}).get('return'))
    service_type: ServiceType = Field(default_factory=lambda data: get_service_type_from_handler(data["tool_call"]))

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
    tools: list[RestateTool] = Field(default=[])
    handoffs: list[str] = Field(default=[]) # agent names

    def to_tool_schema(self) -> dict[str, Any]:
        return {
        "type": "function",
        "name": f"{format_name(self.name)}",
        "description": self.handoff_description,
        "parameters": to_strict_json_schema(Empty),
        "strict": True
    }


class ChatResponse(BaseModel):
    agent: Optional[str]
    messages: list[dict[str, Any]]


def get_service_type_from_handler(handler: Callable[[Any, I], Awaitable[O]]) -> ServiceType:
    handler_annotations = getattr(handler, '__annotations__', {})
    context_type = handler_annotations.get('ctx')
    if issubclass(context_type, restate.Context):
        return "Service"
    elif issubclass(context_type, restate.ObjectContext) or issubclass(context_type, restate.ObjectSharedContext):
        return "VirtualObject"
    elif issubclass(context_type, restate.WorkflowContext) or issubclass(context_type, restate.WorkflowSharedContext):
        return "Workflow"
    else:
        raise TerminalError(f"Could not determine service type for handler {handler}")


def format_name(name: str) -> str:
    return name.replace(" ", "_").lower()


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

    # TODO make the input items a separate class
    input_items = await ctx.get("input_items") or []
    input_items.append({"role": "user", "content": message})
    logger.info(f"Current input items: {input_items}")

    while True:
        tools = {format_name(tool.name): tool for tool in agent.tools}
        tool_and_handoff_schemas = {format_name(tool.name): tool.to_tool_schema() for tool in agent.tools}
        tool_and_handoff_schemas.update({format_name(agent_name): agents_dict[format_name(agent_name)].to_tool_schema() for agent_name in agent.handoffs})

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
                input_items.append({
                    "role": "system",
                    "content": f"Transferred to {agent.name}.",
                })
                ctx.set("input_items", input_items)
            # Execute handler tool
            else:
                input_items.append({
                    "role": "system",
                    "content": f"Executing tool {command.name}.",
                })
                ctx.set("input_items", input_items)

                result = await execute_tool_call(ctx, command, tools[command.name])
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
                            tool_to_call: RestateTool):
    if tool_to_call.service_type == "Service":
        return await ctx.service_call(tool_to_call.tool_call, arg=tool_to_call.input_type(**json.loads(command_message.arguments)))
    elif tool_to_call.service_type == "VirtualObject":
        return await ctx.object_call(tool_to_call.tool_call, key="123", arg=tool_to_call.input_type(**json.loads(command_message.arguments)))
    elif tool_to_call.service_type == "Workflow":
        return await ctx.workflow_call(tool_to_call.tool_call, key="123", arg=tool_to_call.input_type(**json.loads(command_message.arguments)))
    else:
        TerminalError(f"Cannot invoke tool with service type {tool_to_call.service_type}")