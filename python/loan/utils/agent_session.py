import json
import logging
import restate

from datetime import timedelta
from typing import (
    Optional,
    Any,
    Callable,
    Awaitable,
    TypeVar,
    Type,
    List,
    Literal,
    TypedDict,
)
from openai import OpenAI
from openai.lib._pydantic import to_strict_json_schema
from openai.types.responses import (
    ResponseFunctionToolCall,
    Response,
    ResponseOutputMessage,
    ResponseFileSearchToolCall,
    ResponseFunctionWebSearch,
    ResponseReasoningItem,
    ResponseComputerToolCall, ResponseOutputText,
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

# PROMPTS

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
    "If you want to run a tool, then do this before generating the output message. Never return a tool call together with an output message."
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


# MODELS AND TYPES

# Three types of Restate services
ServiceType = Literal["Service", "VirtualObject", "Workflow"]


class Empty(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RestateRequest(BaseModel, Generic[I]):
    """
    Represents a request to a Restate service.

    Attributes:
        key (str): The unique identifier for the Virtual Object or Workflow which contains the tool.
        req (I): The request to be passed to the tool.
        delay_in_millis (int): The delay in milliseconds to delay the task with.
    """

    key: str
    req: I | Empty
    delay_in_millis: int | None


class RestateTool(BaseModel, Generic[I, O]):
    """
    Represents a Restate tool.

    Attributes:
        service_name (str): The name of the service that provides the tool.
        name (str): The name of the tool, equal to the name of the service handler.
        description (str): A description of the tool, to be used by the agent.
        service_type (ServiceType): The type of the service (Service, VirtualObject, or Workflow).
        tool_schema (dict[str, Any]): The schema for the tool's input and output.
        formatted_name (str): The formatted name of the tool without spaces and lowercase, used for the LLM.
    """

    service_name: str
    name: str
    description: str
    service_type: ServiceType
    tool_schema: dict[str, Any]
    formatted_name: str = Field(default_factory=lambda data: format_name(data["name"]))


class Agent(BaseModel):
    """
    Represents an agent in the system.

    Attributes:
        name (str): The name of the agent.
        handoff_description (str): A description of the agent, to be used by the LLM.
        instructions (str): Instructions for the agent, to be used by the LLM.
        tools (list[RestateTool]): A list of tools that the agent can use.
        handoffs (list[str]): A list of handoff agents to which the agent can hand off the conversation.
        formatted_name (str): The formatted name of the agent without spaces and lowercase, used for the LLM.
    """

    name: str
    handoff_description: str
    instructions: str
    tools: list[RestateTool] = Field(default=[])
    handoffs: list[str] = Field(default=[])  # agent names
    formatted_name: str = Field(default_factory=lambda data: format_name(data["name"]))

    def to_tool_schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "name": f"{format_name(self.name)}",
            "description": self.handoff_description,
            "parameters": to_strict_json_schema(Empty),
            "strict": True,
        }

    def as_tool(self, name: str, description: str):
        tool = restate_tool(run)
        tool.description = (
            f"{description} \n {self.handoff_description} \n {tool.description}"
        )
        tool.name = f"{name}_as_tool"
        return tool


class AgentInput(BaseModel):
    """
    The input of an agent session run.

    Attributes:
        starting_agent (Agent): the agent to start the interaction with
        agents (list[Agent]): all the agents that can be part of the interaction
        message (str): input message for the agent
    """

    starting_agent: Agent
    agents: list[Agent]
    message: str


class AgentResponse(BaseModel):
    """
    Represents the response from an agent session.

    Attributes:
        agent (str): The name of the agent that generated the response.
        messages (list[dict[str, Any]]): The messages generated during the session.
        final_output (str): The final output of the agent.
    """

    agent: Optional[str]
    messages: list[dict[str, Any]]
    final_output: str


class SessionItem(TypedDict):
    """
    Represents a single item in the session.

    Attributes:
        role (str): The role of who generated the item, either "user", "assistant", or "system".
        content (str): The content of the item.
    """

    role: Literal["user", "assistant", "system"]
    content: str


class SessionState:
    """
    Represents the state of the session.
    """

    def __init__(self, input_items: Optional[List[SessionItem]] = None):
        self._input_items: List[SessionItem] = input_items or []
        self._new_items: List[SessionItem] = []

    def add_user_message(self, ctx: restate.ObjectContext, item: str):
        user_message = SessionItem(content=item, role="user")
        self._input_items.append(user_message)
        ctx.set("input_items", self._input_items)
        self._new_items.append(user_message)

    def add_user_messages(self, ctx: restate.ObjectContext, items: List[str]):
        user_messages = [SessionItem(content=item, role="user") for item in items]
        self._input_items.extend(user_messages)
        ctx.set("input_items", self._input_items)
        self._new_items.extend(user_messages)

    def add_system_message(self, ctx: restate.ObjectContext, item: str):
        system_message = SessionItem(content=item, role="system")
        self._input_items.append(system_message)
        ctx.set("input_items", self._input_items)
        self._new_items.append(system_message)

    def add_system_messages(self, ctx: restate.ObjectContext, items: List[str]):
        system_messages = [SessionItem(content=item, role="system") for item in items]
        self._input_items.extend(system_messages)
        ctx.set("input_items", self._input_items)
        self._new_items.extend(system_messages)

    def get_input_items(self) -> List[SessionItem]:
        return self._input_items

    def get_new_items(self) -> List[SessionItem]:
        return self._new_items


# AGENT SESSION

agent_session = restate.VirtualObject("AgentSession")


@agent_session.handler()
async def run(ctx: restate.ObjectContext, req: AgentInput) -> AgentResponse:
    """
    Runs an end-to-end agent interaction:
    1. calls the LLM with the input
    2. runs all tools and handoffs
    3. keeps track of the session data: history and current agent

    returns the new items generated

    Args:
        req (AgentInput): The input for the agent
    """

    # === 1. initialize the agent session ===
    session_state = SessionState(input_items=await ctx.get("input_items"))
    session_state.add_user_message(ctx, req.message)

    agent_name = await ctx.get("agent_name") or req.starting_agent.formatted_name
    ctx.set("agent_name", agent_name)
    agents_dict = {agent.formatted_name: agent for agent in req.agents}
    agent = agents_dict[agent_name]

    # === 2. Run the agent loop ===
    while True:
        # Get the tools in the right format for the LLM
        tools = {tool.formatted_name: tool for tool in agent.tools}
        tool_and_handoffs_list = [tool.tool_schema for tool in agent.tools]
        tool_and_handoffs_list.extend(
            [
                agents_dict[format_name(agent_name)].to_tool_schema()
                for agent_name in agent.handoffs
            ]
        )

        # Call the LLM - OpenAPI Responses API
        response: Response = await ctx.run(
            "Call LLM",
            lambda: client.responses.create(
                model="gpt-4o",
                instructions=agent.instructions,
                input=session_state.get_input_items(),
                tools=tool_and_handoffs_list,
                parallel_tool_calls=True,
                stream=False,
            ),
            serde=PydanticJsonSerde(Response),
        )

        # Register the output in the session state
        session_state.add_system_messages(
            ctx, [item.model_dump_json() for item in response.output]
        )

        # Parse LLM response
        tool_calls = []
        run_handoffs = []
        output_messages = []

        for item in response.output:
            if isinstance(item, ResponseOutputMessage):
                output_messages.append(item)
            elif (
                isinstance(item, ResponseFileSearchToolCall)
                or isinstance(item, ResponseFunctionWebSearch)
                or isinstance(item, ResponseReasoningItem)
                or isinstance(item, ResponseComputerToolCall)
            ):
                logger.warning(
                    "This implementation does not support file search, web search, computer tools, or reasoning yet."
                )
                # We add it to the session_state to feed it back into the next LLM call
                session_state.add_system_message(
                    ctx,
                    "This agent cannot handle file search, web search, computer tools, or reasoning. Use another tool or handoff.",
                )
            elif isinstance(item, ResponseFunctionToolCall):
                if item.name in agents_dict.keys():
                    # Handoffs
                    run_handoffs.append(item)
                else:
                    # Tool calls
                    if item.name not in tools.keys():
                        logger.warning(f"Unkown tool, ignoring: {item.name}")
                        session_state.add_system_message(
                            ctx,
                            f"This agent does not have access to this tool: {item.name}. Use another tool or handoff.",
                        )
                    tool_calls.append(item)
            else:
                logger.warning(f"Unexpected output type, ignoring: {type(item)}")
                # We add it to the session_state to feed it back into the next LLM call
                session_state.add_system_message(
                    ctx,
                    f"This agent cannot handle this output type {type(item)}. Use another tool or handoff.",
                )
                continue

        # Execute (parallel) tool calls
        parallel_tools = []
        for command in tool_calls:
            session_state.add_system_message(
                ctx, f"Executing tool {command.name} with args {command.arguments}."
            )

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
                # Used for scheduling tasks in the future or long-running tasks like workflows
                ctx.generic_send(
                    service=tool_to_call.service_name,
                    handler=tool_to_call.name,
                    arg=input_serialized,
                    key=tool_request["key"],
                    send_delay=timedelta(milliseconds=tool_request["delay_in_millis"]),
                )
            session_state.add_system_message(
                ctx, f"Task {tool_to_call.name} was scheduled"
            )

        if len(parallel_tools) > 0:
            results_done = await restate.gather(*parallel_tools)
            results = [(await result).decode() for result in results_done]
            session_state.add_system_messages(ctx, results)

        # Handle handoffs
        if len(run_handoffs) > 0:
            # Only one agent can be in charge of the conversation at a time.
            # So if there are multiple handoffs in the response, only run the first one.
            # For the others, we add a tool response that we will not handle them.
            if len(run_handoffs) > 1:
                session_state.add_system_messages(
                    ctx,
                    [
                        f"Multiple handoffs detected, ignoring this one: {handoff.name} with arguments {handoff.arguments}."
                        for handoff in run_handoffs[1:]
                    ],
                )

            handoff_command = run_handoffs[0]

            # Determine the new agent in charge
            agent = agents_dict[handoff_command.name]
            session_state.add_system_message(ctx, f"Transferred to {agent.name}.")
            ctx.set("agent_name", format_name(agent.name))

            # Start a new agent loop with the new agent
            continue

        # Handle output messages
        # If there are no output messages, then we just continue the loop
        if len(output_messages) > 0:
            if len(output_messages) > 1:
                logger.warning("Multiple output messages in the LLM response.")

            # Use the last output message as the final output
            # If that is a refusal, then just run the loop again
            last_content = output_messages[-1].content[-1]
            if isinstance(last_content, ResponseOutputText):
                final_output = last_content.text
                return AgentResponse(
                    agent=agent.name,
                    messages=session_state.get_new_items(),
                    final_output=final_output,
                )


# UTILS


def format_name(name: str) -> str:
    return name.replace(" ", "_").lower()


def restate_tool(tool_call: Callable[[Any, I], Awaitable[O]]) -> RestateTool:
    target_handler = handler_from_callable(tool_call)
    service_type = get_service_type_from_handler(tool_call)
    match service_type:
        case "VirtualObject":
            description = (
                f"{VIRTUAL_OBJECT_HANDLER_TOOL_PREFIX} \n{target_handler.description}"
            )
        case "Workflow":
            description = (
                f"{WORKFLOW_HANDLER_TOOL_PREFIX} \n{target_handler.description}"
            )
        case _:
            description = target_handler.description

    return RestateTool(
        service_name=target_handler.service_tag.name,
        name=target_handler.name,
        description=target_handler.description,
        service_type=service_type,
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


def get_input_type_from_handler(handler: Callable[[Any, I], Awaitable[O]]) -> Type[I]:
    handler_annotations = getattr(handler, "__annotations__", {})
    # The annotations contain the context type (key "ctx"), request type and return type (key "return").
    # The input type is in the annotations with as key the name of the variable in the function.
    # Since this can be anything, we search for the value that is not called "ctx" or "return".
    input_type = next(
        (v for k, v in handler_annotations.items() if k not in {"ctx", "return"}), Empty
    )
    return input_type


def get_service_type_from_handler(
    handler: Callable[[Any, I], Awaitable[O]],
) -> ServiceType:
    handler_annotations = getattr(handler, "__annotations__", {})
    ctx_type = handler_annotations.get("ctx")
    match ctx_type:
        case _ if issubclass(ctx_type, restate.Context):
            return "Service"
        case _ if issubclass(ctx_type, restate.ObjectContext) or issubclass(
            ctx_type, restate.ObjectSharedContext
        ):
            return "VirtualObject"
        case _ if issubclass(ctx_type, restate.WorkflowContext) or issubclass(
            ctx_type, restate.WorkflowSharedContext
        ):
            return "Workflow"
        case _:
            raise TerminalError(
                f"Could not determine service type for handler {handler}"
            )
