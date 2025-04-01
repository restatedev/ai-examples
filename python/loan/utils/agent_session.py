import copy
import json
import logging
from datetime import timedelta
from typing import Optional, Any, Callable, Awaitable, TypeVar, Type, List, Literal

import restate
from openai import OpenAI
from openai.lib._pydantic import to_strict_json_schema
from openai.types.responses import (
    ResponseFunctionToolCall,
    Response,
    ResponseOutputMessage, ResponseInputParam, ResponseOutputItem,
)
from pydantic import BaseModel, ConfigDict, Field
from restate import TerminalError
from restate.handler import handler_from_callable
from restate.serde import PydanticJsonSerde
from typing_extensions import Generic

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

I = TypeVar("I", bound=BaseModel)
O = TypeVar("O", bound=BaseModel)

client = OpenAI()

# prompt prefix for agents
RECOMMENDED_PROMPT_PREFIX = (
    "# System context\n"
    "You are part of a multi-agent system called the Agents SDK, designed to make agent "
    "coordination and execution easy. Agents uses two primary abstraction: **Agents** and "
    "**Handoffs**. An agent encompasses instructions and tools and can hand off a "
    "conversation to another agent when appropriate. "
    "Handoffs are achieved by calling a handoff function, generally having the word '_agent' in their name. "
    "Transfers between agents are handled seamlessly in the background;"
    " do not mention or draw attention to these transfers in your conversation with the user.\n"
    "You can run tools in parallel but you can only hand off to at most one agent. Never suggest handing off to two or more."
)

# prompt prefix for tools; gets added to the tool description
VIRTUAL_OBJECT_HANDLER_TOOL_PREFIX = (
    "# System context\n"
    "This tool is part of a Virtual Object. Virtual Objects are keyed services that need to be addressed by specifying the key. "
    "The key is a unique identifier for the object. "
    "The key makes sure that you get access to the correct object so it is really important that this is correct. "
    "The key is a string. In case there is the slightest doubt about the key, always ask the user for the key. "
    "The key is part of the input schema of the tool. You can find the meaning of the key in the tool's input schema. "
    "Keys usually present a unique identifier for the object: for example a customer virtual object might have the customer id as key. "
    "Unless the agent really explicitly asks to only schedule the task, set delay to None because then you will be able to retrieve the response."
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
    delay_in_millis: int | None


ServiceType = Literal["Service", "VirtualObject", "Workflow"]


class RestateTool(BaseModel, Generic[I, O]):
    service_name: str
    name: str
    description: str
    service_type: ServiceType
    tool_schema: dict[str, Any]


def get_input_type_from_handler(handler: Callable[[Any, I], Awaitable[O]]) -> Type[I]:
    handler_annotations = getattr(handler, "__annotations__", {})
    # The annotations contain the context type (key "ctx"), request type and return type (key "return").
    # The input type is in the annotations with as key the name of the variable in the function.
    # Since this can be anything, we search for the value that is not called "ctx" or "return".
    input_type = next(
        (v for k, v in handler_annotations.items() if k not in {"ctx", "return"}), Empty
    )
    return input_type


def restate_tool(tool_call: Callable[[Any, I], Awaitable[O]]) -> RestateTool:
    target_handler = handler_from_callable(tool_call)
    service_type = get_service_type_from_handler(tool_call)
    if service_type == "VirtualObject":
        description = f"{VIRTUAL_OBJECT_HANDLER_TOOL_PREFIX} \n{target_handler.description}"
    elif service_type == "Workflow":
        description = f"{WORKFLOW_HANDLER_TOOL_PREFIX} \n{target_handler.description}"
    else:
        description = target_handler.description

    return RestateTool(
        service_name=target_handler.service_tag.name,
        name=target_handler.name,
        description=target_handler.description,
        service_type=get_service_type_from_handler(tool_call),
        tool_schema={
            "type": "function",
            "name": f"{target_handler.name}",
            "description": description,
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


def agent_as_tool(agent: Agent, name: str, description: str):
    tool = restate_tool(run)
    tool.description = f"{description} \n {agent.handoff_description} \n {tool.description}"
    tool.name = f"{name}_as_tool"
    return tool


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
    """
    The input of an agent session run.

    Args:
        starting_agent (Agent): the agent to start the interaction with
        agents (list[Agent]): all the agents that can be part of the interaction
        message (str): input message for the agent
        input_items (ResponseInputParam): input items to use for the agents
    """
    starting_agent: Agent
    agents: list[Agent]
    message: str
    input_items: ResponseInputParam = Field(default=[])


@agent_session.handler()
async def run(ctx: restate.ObjectContext, req: AgentInput) -> ChatResponse:
    """
    Runs an end-to-end agent interaction:
    1. calls the LLM with the input
    2. runs all tools and handoffs
    3. keeps track of the session data: history and current agent

    returns the new items generated

    Args:
        req (AgentInput): The input for the agent
    """
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
    input_items.extend(req.input_items)
    input_items.append({"role": "user", "content": req.message})

    new_items = []

    while True:
        tools = {format_name(tool.name): tool for tool in agent.tools}
        tool_and_handoffs_list = [tool.tool_schema for tool in agent.tools]
        tool_and_handoffs_list.extend(
            [
                agents_dict[format_name(agent_name)].to_tool_schema()
                for agent_name in agent.handoffs
            ]
        )

        response: Response = await ctx.run(
            "Call LLM",
            lambda: client.responses.create(
                model="gpt-4o",
                instructions=agent.instructions,
                input=input_items,
                tools=tool_and_handoffs_list,
                parallel_tool_calls=True,
                stream=False,
            ),
            serde=PydanticJsonSerde(Response),
        )

        output: List[ResponseOutputItem] = copy.deepcopy(response.output)

        print(output)

        new_items.extend(
            [
                {"role": "system", "content": item.model_dump_json()}
                for item in output
            ]
        )
        input_items.extend(
            [
                {"role": "system", "content": item.model_dump_json()}
                for item in output
            ]
        )
        ctx.set("input_items", input_items)

        print(f"{agent.name}:", output)
        # === 2. handle (parallel) tool calls ===

        response_output_messages = [
            item for item in output
            if isinstance(item, ResponseOutputMessage)
        ]

        # TODO should we still run the tools if we already have an output message?
        # If so, this needs to be moved lower.
        if len(response_output_messages) == 1:
            break
        elif len(response_output_messages) > 1:
            logger.warning("Multiple output messages in the LLM response.")

        response_tool_calls_and_handoffs: List[ResponseFunctionToolCall] = [
            item for item in output
            if not isinstance(item, ResponseOutputMessage)
        ]

        handoffs = [
            item for item in response_tool_calls_and_handoffs
            if item.name in agents_dict.keys()
        ]
        if len(handoffs) == 1:
            handoff_command = handoffs[0]
            agent = agents_dict[handoff_command.name]

            msg = {
                "role": "system",
                "content": f"Transferred to {agent.name}.",
            }
            new_items.append(msg)
            input_items.append(msg)
            ctx.set("current_agent_name", format_name(agent.name))
            ctx.set("input_items", input_items)

        if len(handoffs) > 1:
            # What to do in this case? This shouldn't happen...
            raise TerminalError("Multiple handoffs in the LLM response.")

        tool_calls = [
            item for item in response_tool_calls_and_handoffs
            if item.name not in agents_dict.keys()
        ]

        parallel_tools = []
        for command in tool_calls:
            msg = {
                    "role": "system",
                    "content": f"Executing tool {command.name} with arguments {command.arguments}.",
                }
            new_items.append(msg)
            input_items.append(msg)
            ctx.set("input_items", input_items)

            # This can either return a sync response or a call handle
            # If it is a call handle then we add it to the list
            tool_to_call = tools[command.name]
            tool_request = json.loads(command.arguments)
            if tool_request.get("req") is None:
                input_serialized = bytes({})
            else:
                input_serialized = json.dumps(tool_request["req"]).encode()

            if tool_request.get("delay_in_millis") is None:
                handle = ctx.generic_call(
                    service=tool_to_call.service_name,
                    handler=tool_to_call.name,
                    arg=input_serialized,
                    key=tool_request["key"],
                )
                parallel_tools.append(handle)
            else:
                ctx.generic_send(
                    service=tool_to_call.service_name,
                    handler=tool_to_call.name,
                    arg=input_serialized,
                    key=tool_request["key"],
                    send_delay=timedelta(milliseconds=tool_request["delay_in_millis"]),
                )
                msg = {
                    "role": "system",
                    "content": f"Task {tool_to_call.name} was scheduled",
                }
                new_items.append(msg)
                input_items.append(msg)


        if len(parallel_tools) > 0:
            results_done = await restate.gather(*parallel_tools)
            results = [(await result).decode() for result in results_done]
            result_msgs = [{
                "role": "system",
                "content": result,
            } for result in results]
            new_items.extend(result_msgs)
            input_items.extend(result_msgs)

        ctx.set("input_items", input_items)

    return ChatResponse(agent=agent.name, messages=new_items)