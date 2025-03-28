import json
import logging
import typing
from datetime import timedelta
from typing import Optional, Any, Callable, Awaitable, TypeVar, Type

import restate
from openai import OpenAI
from openai.lib._pydantic import to_strict_json_schema
from openai.types.responses import (
    ResponseFunctionToolCall,
    Response,
    ResponseOutputMessage,
)
from pydantic import BaseModel, ConfigDict, Field
from restate import TerminalError
from restate.handler import handler_from_callable, TypeHint
from restate.serde import PydanticJsonSerde, Serde
from typing_extensions import Generic

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

I = TypeVar("I", bound=BaseModel)
O = TypeVar("O", bound=BaseModel)

client = OpenAI()

RECOMMENDED_PROMPT_PREFIX = (
    "# System context\n"
    "You are part of a multi-agent system called the Agents SDK, designed to make agent "
    "coordination and execution easy. Agents uses two primary abstraction: **Agents** and "
    "**Handoffs**. An agent encompasses instructions and tools and can hand off a "
    "conversation to another agent when appropriate. "
    "Handoffs are achieved by calling a handoff function, generally having the word 'agent' in their name. "
    "Transfers between agents are handled seamlessly in the background;"
    " do not mention or draw attention to these transfers in your conversation with the user.\n"
)

VIRTUAL_OBJECT_HANDLER_TOOL_PREFIX = (
    "# System context\n"
    "This tool is part of a Virtual Object. Virtual Objects are keyed services that need to be addressed by specifying the key. "
    "The key is a unique identifier for the object. "
    "The key makes sure that you get access to the correct object so it is really important that this is correct. "
    "The key is a string. In case there is the slightest doubt about the key, always ask the user for the key. "
    "The key is part of the input schema of the tool. You can find the meaning of the key in the tool's input schema. "
    "Keys usually present a unique identifier for the object: for example a customer virtual object might have the customer id as key. "
)

WORKFLOW_HANDLER_TOOL_PREFIX = (
    "# System context\n"
    "This tool is part of a Workflow. Workflows are keyed services that need to be addressed by specifying the key. "
    "The key is a unique identifier for the workflow. "
    "The key makes sure that you get access to the correct workflow so it is really important that this is correct. "
    "The key is a string. In case there is the slightest doubt about the key, always ask the user for the key. "
    "The key is part of the input schema of the tool. You can find the meaning of the key in the tool's input schema. "
    "Keys usually present a unique identifier for the workflow: for example a customer signup workflow might have the customer id as key. "
    "Unless the agent really explicitly asks to wait for the final result of the workflow, set delay to 0 because this will submit the workflow without waiting for the response."
)


class Empty(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RestateRequest(BaseModel, Generic[I]):
    """
    Represents a request to a Restate service.

    Attributes:
        key (str): The unique identifier for the Virtual Object or Workflow which contains the tool.
        arg (I): The argument to be passed to the tool.
        delay_in_millis (int): The delay in milliseconds to delay the task with.
    """

    key: str
    req: I | Empty
    delay_in_millis: int | None = None


ServiceType = typing.Literal["Service", "VirtualObject", "Workflow"]


class RestateTool(BaseModel, Generic[I, O]):
    service_name: str
    name: str
    description: str
    service_type: ServiceType
    tool_schema: dict[str, Any]


def get_input_type_from_handler(handler: Callable[[Any, I], Awaitable[O]]) -> Type[I]:
    handler_annotations = getattr(handler, "__annotations__", {})
    input_type = next(
        (v for k, v in handler_annotations.items() if k not in {"ctx", "return"}), Empty
    )
    return input_type


def restate_tool(tool_call: Callable[[Any, I], Awaitable[O]]) -> RestateTool:
    target_handler = handler_from_callable(tool_call)
    return RestateTool(
        service_name=target_handler.service_tag.name,
        name=target_handler.name,
        description=target_handler.description,
        service_type=get_service_type_from_handler(tool_call),
        tool_schema={
            "type": "function",
            "name": f"{target_handler.name}",
            "description": target_handler.description,
            "parameters": to_strict_json_schema(
                RestateRequest[get_input_type_from_handler(tool_call)]
            ),
            "strict": True,
        },
    )


class Agent(BaseModel):
    name: str
    handoff_description: str
    instructions: str
    tools: list[RestateTool] = Field(default=[])
    handoffs: list[str] = Field(default=[])  # agent names

    def to_tool_schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "name": f"{format_name(self.name)}",
            "description": self.handoff_description,
            "parameters": to_strict_json_schema(Empty),
            "strict": True,
        }


class ChatResponse(BaseModel):
    agent: Optional[str]
    messages: list[dict[str, Any]]


def get_service_type_from_handler(
    handler: Callable[[Any, I], Awaitable[O]],
) -> ServiceType:
    handler_annotations = getattr(handler, "__annotations__", {})
    context_type = handler_annotations.get("ctx")
    if issubclass(context_type, restate.Context):
        return "Service"
    elif issubclass(context_type, restate.ObjectContext) or issubclass(
        context_type, restate.ObjectSharedContext
    ):
        return "VirtualObject"
    elif issubclass(context_type, restate.WorkflowContext) or issubclass(
        context_type, restate.WorkflowSharedContext
    ):
        return "Workflow"
    else:
        raise TerminalError(f"Could not determine service type for handler {handler}")


def format_name(name: str) -> str:
    return name.replace(" ", "_").lower()


agent_session = restate.VirtualObject("AgentSession")


class AgentInput(BaseModel):
    starting_agent: Agent
    agents: list[Agent]
    message: str


@agent_session.handler()
async def run(ctx: restate.ObjectContext, req: AgentInput) -> ChatResponse:
    current_agent_name: str = await ctx.get("current_agent_name") or format_name(
        req.starting_agent.name
    )
    ctx.set("current_agent_name", current_agent_name)
    logger.info(f"Running chat workflow for: {current_agent_name}")

    agents_dict = {format_name(agent.name): agent for agent in req.agents}
    agent = agents_dict[current_agent_name]
    logger.info(f"Agent at disposal: {agents_dict}")

    # TODO make the input items a separate class
    input_items = await ctx.get("input_items") or []
    input_items.append({"role": "user", "content": req.message})
    logger.info(f"Current input items: {input_items}")

    while True:
        tools = {format_name(tool.name): tool for tool in agent.tools}
        tool_and_handoffs_list = [tool.tool_schema for tool in agent.tools]
        tool_and_handoffs_list.extend(
            [
                agents_dict[format_name(agent_name)].to_tool_schema()
                for agent_name in agent.handoffs
            ]
        )

        response = await ctx.run(
            "Call LLM",
            lambda: client.responses.create(
                model="gpt-4o",
                instructions=agent.instructions,
                input=input_items,
                tools=tool_and_handoffs_list,
                stream=False,
            ),
            serde=PydanticJsonSerde(Response),
        )

        input_items.extend(
            [
                {"role": "system", "content": item.model_dump_json()}
                for item in response.output
            ]
        )
        ctx.set("input_items", input_items)

        # TODO this is a list; handle the other output items
        command = response.output[0]
        print(f"{agent.name}:", command)

        # === 2. handle tool calls ===
        if isinstance(command, ResponseFunctionToolCall):
            # Handoffs
            if command.name in agents_dict.keys():
                agent = agents_dict[command.name]
                input_items.append(
                    {
                        "role": "system",
                        "content": f"Transferred to {agent.name}.",
                    }
                )
                ctx.set("input_items", input_items)
            # Execute handler tool
            else:
                input_items.append(
                    {
                        "role": "system",
                        "content": f"Executing tool {command.name}.",
                    }
                )
                ctx.set("input_items", input_items)

                result = await execute_tool_call(ctx, command, tools[command.name])
                input_items.append(
                    {
                        "role": "system",
                        "content": result,
                    }
                )
                ctx.set("input_items", input_items)
        if isinstance(command, ResponseOutputMessage):
            break

    ctx.set("input_items", input_items)
    ctx.set("current_agent_name", format_name(agent.name))

    return ChatResponse(agent=agent.name, messages=input_items)


async def execute_tool_call(
    ctx: restate.ObjectContext,
    command_message: ResponseFunctionToolCall,
    tool_to_call: RestateTool,
):
    request = json.loads(command_message.arguments)
    if request.get("req") is None:
        input_serialized = bytes({})
    else:
        input_serialized = json.dumps(request["req"]).encode()

    if request.get("delay_in_millis") is not None:
        ctx.generic_send(
            service=tool_to_call.service_name,
            handler=tool_to_call.name,
            arg=input_serialized,
            key=request["key"],
            send_delay=timedelta(milliseconds=request["delay_in_millis"]),
        )
        return "Task was scheduled"
    else:
        result = await ctx.generic_call(
            service=tool_to_call.service_name,
            handler=tool_to_call.name,
            arg=input_serialized,
            key=request["key"],
        )
        return result.decode()
