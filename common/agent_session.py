import json
import logging
import uuid
import httpx
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
    Dict,
)

from openai import OpenAI
from openai.lib._pydantic import to_strict_json_schema
from openai.types.responses import (
    ResponseFunctionToolCall,
    Response,
    ResponseOutputMessage,
    ResponseOutputItem,
)
from pydantic import BaseModel, ConfigDict, Field
from restate import TerminalError
from restate.handler import handler_from_callable
from typing_extensions import Generic

from .models import (
    AgentCard,
    AgentSkill,
    AgentCapabilities,
    TaskSendParams,
    Task,
    SendTaskRequest,
    SendTaskResponse,
    JSONRPCRequest,
    Message,
    TextPart,
    TaskState,
)

logger = logging.getLogger(__name__)

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
class Empty(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AgentError(Exception):
    """
    Errors that should be fed back into the next agent loop.
    """

    def __init__(self, message: str):
        self.message = message
        super().__init__(f"Agent Error: {message}")


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
        service_type (str): The type of the service (service, object, or workflow).
        tool_schema (dict[str, Any]): The schema for the tool's input and output.
        formatted_name (str): The formatted name of the tool without spaces and lowercase, used for the LLM.
    """

    service_name: str
    name: str
    description: str
    service_type: str
    tool_schema: dict[str, Any]
    formatted_name: str = Field(default_factory=lambda data: format_name(data["name"]))

    def as_agent_skill(self) -> AgentSkill:
        return AgentSkill(
            id=self.formatted_name,
            name=self.name,
            description=self.description,
        )


class RemoteAgentMessage(BaseModel):
    """
    Represents a message to be sent to a remote agent.
    The message should include the instructions of what the agent should do.
    It should include a copy of the user input, together with the context/history that is relevant for the task.

    Attributes:
        message (str): The message to send to the agent for the task.
    """

    message: str


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
    instructions: str | None = None
    tools: list[RestateTool] = Field(default_factory=list)
    handoffs: list[str] = Field(default_factory=list)  # agent names
    formatted_name: str = Field(default_factory=lambda data: format_name(data["name"]))
    remote_url: str | None = None
    streaming_support: bool = False
    push_notifications_support: bool = False

    def to_tool_schema(self) -> dict[str, Any]:
        schema = to_strict_json_schema(RemoteAgentMessage if self.remote_url else Empty)
        return {
            "type": "function",
            "name": f"{format_name(self.name)}",
            "description": self.handoff_description,
            "parameters": schema,
            "strict": True,
        }

    def as_tool(self, name: str, description: str):
        tool = restate_tool(run_agent_session)
        tool.description = (
            f"{description} \n {self.handoff_description} \n {tool.description}"
        )
        tool.name = f"{name}_as_tool"
        return tool

    def as_agent_card(self) -> AgentCard:
        return AgentCard(
            name=self.name,
            description=self.handoff_description,
            url=self.remote_url,
            version="0.0.1",
            capabilities=AgentCapabilities(
                streaming=self.streaming_support,
                pushNotifications=self.push_notifications_support,
            ),
            # TODO include handoffs?
            skills=[tool.as_agent_skill() for tool in self.tools],
        )


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


class ToolCall(BaseModel):
    name: str
    tool: RestateTool
    key: str | None
    input_bytes: bytes
    delay_in_millis: int | None


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
        self.state_name = "agent_state"

    def add_user_message(self, ctx: restate.ObjectContext, item: str):
        user_message = SessionItem(content=item, role="user")
        self._input_items.append(user_message)
        ctx.set(self.state_name, self._input_items)
        self._new_items.append(user_message)

    def add_user_messages(self, ctx: restate.ObjectContext, items: List[str]):
        user_messages = [SessionItem(content=item, role="user") for item in items]
        self._input_items.extend(user_messages)
        ctx.set(self.state_name, self._input_items)
        self._new_items.extend(user_messages)

    def add_system_message(self, ctx: restate.ObjectContext, item: str):
        system_message = SessionItem(content=item, role="system")
        self._input_items.append(system_message)
        self._new_items.append(system_message)
        ctx.set(self.state_name, self._input_items)

    def add_system_messages(self, ctx: restate.ObjectContext, items: List[str]):
        system_messages = [SessionItem(content=item, role="system") for item in items]
        self._input_items.extend(system_messages)
        ctx.set(self.state_name, self._input_items)
        self._new_items.extend(system_messages)

    def get_input_items(self) -> List[SessionItem]:
        return self._input_items

    def get_new_items(self) -> List[SessionItem]:
        return self._new_items


# AGENT SESSION
# Option 1: run the agent session as a separate service
agent_session = restate.VirtualObject("AgentSession")


@agent_session.handler()
async def run_agent_session(
    ctx: restate.ObjectContext, req: AgentInput
) -> AgentResponse:
    return await run_agent(ctx, req)


# Option 2: call this method immediately from the chat session/workflow
async def run_agent(ctx: restate.ObjectContext, req: AgentInput) -> AgentResponse:
    """
    Runs an end-to-end agent interaction:
    1. calls the LLM with the input
    2. runs all tools and handoffs
    3. keeps track of the session data: history and current agent

    returns the new items generated

    Args:
        req (AgentInput): The input for the agent
    """
    log_prefix = f"{ctx.request().id} - agent-session {ctx.key()}- - "

    # === 1. initialize the agent session ===
    logging.info(f"{log_prefix} Starting agent session")
    session_state = SessionState(input_items=await ctx.get("agent_state"))
    session_state.add_user_message(ctx, req.message)

    agent_name = await ctx.get("agent_name") or req.starting_agent.formatted_name
    ctx.set("agent_name", agent_name)

    agents_dict = {a.formatted_name: a for a in req.agents}
    agent = agents_dict.get(agent_name)

    if agent is None:
        raise TerminalError(
            f"Agent {agent_name} not found in the list of agents: {list(agents_dict.keys())}"
        )

    # === 2. Run the agent loop ===
    while True:
        # Get the tools in the right format for the LLM
        try:
            tools = {tool.formatted_name: tool for tool in agent.tools}
            logger.info(
                f"{log_prefix} Starting iteration of agent: {agent.name} with tools/handoffs: {list(tools.keys())}"
            )

            tool_schemas = [tool.tool_schema for tool in agent.tools]
            for handoff_agent_name in agent.handoffs:
                handoff_agent = agents_dict.get(format_name(handoff_agent_name))
                if handoff_agent is None:
                    logger.warning(
                        f"Agent {handoff_agent_name} not found in the list of agents. Ignoring this handoff agent."
                    )
                tool_schemas.append(handoff_agent.to_tool_schema())

            # Call the LLM - OpenAPI Responses API
            logger.info(f"{log_prefix} Calling LLM")
            response: Response = await ctx.run(
                "Call LLM",
                lambda: client.responses.create(
                    model="gpt-4o",
                    instructions=agent.instructions,
                    input=session_state.get_input_items(),
                    tools=tool_schemas,
                    parallel_tool_calls=True,
                    stream=False,
                ),
                type_hint=Response,
                max_attempts=3,  # To using too many credits on infinite retries during development
            )

            # Register the output in the session state
            session_state.add_system_messages(
                ctx, [item.model_dump_json() for item in response.output]
            )

            # Parse LLM response
            output_messages, run_handoffs, tool_calls = await parse_llm_response(
                agents_dict, response.output, tools
            )

            # Execute (parallel) tool calls
            parallel_tools = []
            for tool_call in tool_calls:
                logger.info(f"{log_prefix} Executing tool {tool_call.name}")
                try:
                    if tool_call.delay_in_millis is None:
                        handle = ctx.generic_call(
                            service=tool_call.tool.service_name,
                            handler=tool_call.tool.name,
                            arg=tool_call.input_bytes,
                            key=tool_call.key,
                        )
                        parallel_tools.append(handle)
                    else:
                        # Used for scheduling tasks in the future or long-running tasks like workflows
                        ctx.generic_send(
                            service=tool_call.tool.service_name,
                            handler=tool_call.tool.name,
                            arg=tool_call.input_bytes,
                            key=tool_call.key,
                            send_delay=timedelta(
                                milliseconds=tool_call.delay_in_millis
                            ),
                        )
                    session_state.add_system_message(
                        ctx, f"Task {tool_call.name} was scheduled"
                    )
                except TerminalError as e:
                    # We add it to the session_state to feed it back into the next LLM call
                    # Let the other parallel tool executions continue
                    session_state.add_system_message(
                        ctx,
                        f"Failed to execute tool {tool_call.name}: {str(e)}",
                    )

            if len(parallel_tools) > 0:
                results_done = await restate.gather(*parallel_tools)
                results = [(await result).decode() for result in results_done]
                session_state.add_system_messages(ctx, results)

            # Handle handoffs
            if run_handoffs:
                # Only one agent can be in charge of the conversation at a time.
                # So if there are multiple handoffs in the response, only run the first one.
                if len(run_handoffs) > 1:
                    logger.info(
                        f"{log_prefix} Multiple handoffs detected. Ignoring: {[h.name for h in run_handoffs[1:]]}"
                    )

                handoff_command = run_handoffs[0]
                next_agent = agents_dict.get(handoff_command.name)
                if next_agent is None:
                    raise AgentError(
                        f"Agent {handoff_command.name} not found in the list of agents."
                    )

                if next_agent.remote_url not in {None, ""}:
                    remote_agent_to_call = agents_dict.get(handoff_command.name)
                    if remote_agent_to_call is None:
                        raise AgentError(
                            f"Agent {handoff_command.name} not found in the list of agents."
                        )

                    logger.info(
                        f"{log_prefix} Calling Remote A2A Agent {handoff_command.name}"
                    )
                    remote_agent_output = await call_remote_agent(
                        ctx,
                        remote_agent_to_call.as_agent_card(),
                        handoff_command.arguments,
                    )
                    session_state.add_system_message(
                        ctx, f"{handoff_command.name} response: {remote_agent_output}"
                    )
                else:
                    # Start a new agent loop with the new agent
                    agent = next_agent
                    ctx.set("agent_name", format_name(agent.name))
                continue

            # Handle output messages
            # If there are no output messages, then we just continue the loop
            final_output = response.output_text
            if final_output != "":
                logger.info(f"{log_prefix} Final output message generated.")
                return AgentResponse(
                    agent=agent.name,
                    messages=session_state.get_new_items(),
                    final_output=final_output,
                )
        except AgentError as e:
            logger.warning(
                f"{log_prefix} Iteration of agent run failed. Updating state and feeding back error to LLM: {str(e)}"
            )
            session_state.add_system_message(
                ctx, f"Failed iteration of agent run: {str(e)}"
            )


async def parse_llm_response(
    agents_dict: Dict[str, Agent],
    output: List[ResponseOutputItem],
    tools: Dict[str, RestateTool],
):
    tool_calls = []
    run_handoffs = []
    output_messages = []
    for item in output:
        if isinstance(item, ResponseOutputMessage):
            output_messages.append(item)

        elif isinstance(item, ResponseFunctionToolCall):
            if item.name in agents_dict.keys():
                # Handoffs
                run_handoffs.append(item)
            else:
                # Tool calls
                if item.name not in tools.keys():
                    # feed error message back to LLM
                    raise AgentError(
                        f"Error while parsing LLM response: This agent does not have access to this tool: {item.name}. Use another tool or handoff."
                    )
                tool = tools[item.name]
                tool_calls.append(to_tool_call(tool, item))
        else:
            # feed error message back to LLM
            raise AgentError(
                f"Error while parsing LLM response: This agent cannot handle this output type {type(item)}. Use another tool or handoff.",
            )

    return output_messages, run_handoffs, tool_calls


def format_name(name: str) -> str:
    return name.replace(" ", "_").lower()


def restate_tool(tool_call: Callable[[Any, I], Awaitable[O]]) -> RestateTool:
    target_handler = handler_from_callable(tool_call)
    service_type = target_handler.service_tag.kind
    input_type = target_handler.handler_io.input_type.annotation
    match service_type:
        case "object":
            description = (
                f"{VIRTUAL_OBJECT_HANDLER_TOOL_PREFIX} \n{target_handler.description}"
            )
        case "workflow":
            description = (
                f"{WORKFLOW_HANDLER_TOOL_PREFIX} \n{target_handler.description}"
            )
        case "service":
            description = target_handler.description
        case _:
            raise TerminalError(
                f"Unknown service type {service_type}. Is this tool a Restate handler?"
            )

    return RestateTool(
        service_name=target_handler.service_tag.name,
        name=target_handler.name,
        description=target_handler.description,
        service_type=service_type,
        tool_schema={
            "type": "function",
            "name": f"{target_handler.name}",
            "description": description,
            "parameters": to_strict_json_schema(RestateRequest[input_type]),
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


def to_tool_call(tool: RestateTool, item: ResponseFunctionToolCall) -> ToolCall:
    tool_request = json.loads(item.arguments)

    if tool_request.get("req") is None:
        input_serialized = bytes({})
    else:
        input_serialized = json.dumps(tool_request["req"]).encode()
    key = None
    if tool.service_type in {"workflow", "object"}:
        key = tool_request.get("key")
        if key is None:
            # feed error message back to LLM
            raise AgentError(
                f"Service key is required for {tool.service_type} ${tool.service_name} but not provided in the request."
            )

    delay_in_millis = tool_request.get("delay_in_millis")
    return ToolCall(
        name=item.name,
        tool=tool,
        key=key,
        input_bytes=input_serialized,
        delay_in_millis=delay_in_millis,
    )


async def call_remote_agent(
    ctx: restate.ObjectContext, card: AgentCard, message: str
) -> Task | None:
    request = await ctx.run(
        "Generate send request",
        lambda: SendTaskRequest(
            id=uuid.uuid4().hex,
            params=TaskSendParams(
                id=uuid.uuid4().hex,
                sessionId=ctx.key(),
                message=Message(role="user", parts=[TextPart(text=message)]),
            ),
        ),
        type_hint=SendTaskRequest,
    )
    logger.info(
        f"Sending request to {card.name} at {card.url} with request payload: {request.model_dump()}"
    )
    response = await ctx.run("Call Agent", send_request, args=(card.url, request))
    logger.info(
        f"Received response from {card.name}: {response.result.model_dump_json()}"
    )

    match response.result.status.state:
        case TaskState.INPUT_REQUIRED:
            final_output = f"MISSING_INFO: {response.result.status.message.parts}"
        case TaskState.COMPLETED:
            final_output = response.result.artifacts
        case TaskState.CANCELED:
            final_output = "Task canceled"
        case TaskState.FAILED:
            final_output = f"Task failed: {response.error.message}"
        case TaskState.SUBMITTED:
            final_output = "Task submitted"
        case TaskState.WORKING:
            final_output = "Task is in progress"
        case _:
            final_output = "Task status unknown"

    return final_output


async def send_request(url: str, request: JSONRPCRequest) -> SendTaskResponse:
    async with httpx.AsyncClient() as client:
        # retry any errors that come out of this
        resp = await client.post(
            url,
            json=request.model_dump(),
            headers={"idempotency-key": request.id},
            timeout=300,
        )
        resp.raise_for_status()

        try:
            return SendTaskResponse(**resp.json())
        except (json.JSONDecodeError, TypeError) as e:
            # feed error message back to LLM
            raise AgentError(
                f"Response was not in A2A SendTaskResponse format. Error: {str(e)}"
            ) from e
