from __future__ import annotations

import asyncio
import copy
import json
import logging
import restate
from restate.exceptions import TerminalError
from dataclasses import dataclass, field
from typing import Any, cast, Dict

from openai.types.responses import (
    ResponseOutputMessage,
    ResponseOutputText,
    ResponseOutputRefusal,
    ResponseFunctionToolCall,
    ResponseComputerToolCall,
    ResponseFileSearchToolCall,
    ResponseFunctionWebSearch
)


from agents.tracing import agent_span
from agents import _utils
from agents._run_impl import (
    RunImpl,
    SingleStepResult,
    NextStepRunAgain,
    NextStepHandoff,
    NextStepFinalOutput,
    TraceCtxManager,
    get_model_tracing_impl,
)
from agents import (
    Agent,
    Model,
    Usage,
    ItemHelpers,
    ModelProvider,
    RunContextWrapper,
    OpenAIProvider,
    RunResult,
    ModelSettings,
    HandoffInputFilter,
    TResponseInputItem,
    InputGuardrail,
    handoff,
    ModelResponse,
    InputGuardrailResult,
    Span,
    SpanError,
    AgentsException,
    OutputGuardrail,
    RunHooks,
    RunItem,
    AgentOutputSchema,
    Handoff,
    AgentSpanData,
    InputGuardrailTripwireTriggered,
    OutputGuardrailResult,
    OutputGuardrailTripwireTriggered,
)

DEFAULT_MAX_TURNS = 10


@dataclass
class RunConfig:
    """Configures settings for the entire agent run."""

    model: str | Model | None = None
    """The model to use for the entire agent run. If set, will override the model set on every
    agent. The model_provider passed in below must be able to resolve this model name.
    """

    model_provider: ModelProvider = field(default_factory=OpenAIProvider)
    """The model provider to use when looking up string model names. Defaults to OpenAI."""

    model_settings: ModelSettings | None = None
    """Configure global model settings. Any non-null values will override the agent-specific model
    settings.
    """

    handoff_input_filter: HandoffInputFilter | None = None
    """A global input filter to apply to all handoffs. If `Handoff.input_filter` is set, then that
    will take precedence. The input filter allows you to edit the inputs that are sent to the new
    agent. See the documentation in `Handoff.input_filter` for more details.
    """

    input_guardrails: list[InputGuardrail[Any]] | None = None
    """A list of input guardrails to run on the initial run input."""

    output_guardrails: list[OutputGuardrail[Any]] | None = None
    """A list of output guardrails to run on the final output of the run."""

    tracing_disabled: bool = False
    """Whether tracing is disabled for the agent run. If disabled, we will not trace the agent run.
    """

    trace_include_sensitive_data: bool = True
    """Whether we include potentially sensitive data (for example: inputs/outputs of tool calls or
    LLM generations) in traces. If False, we'll still create spans for these events, but the
    sensitive data will not be included.
    """

    workflow_name: str = "Agent workflow"
    """The name of the run, used for tracing. Should be a logical name for the run, like
    "Code generation workflow" or "Customer support agent".
    """

    trace_id: str | None = None
    """A custom trace ID to use for tracing. If not provided, we will generate a new trace ID."""

    group_id: str | None = None
    """
    A grouping identifier to use for tracing, to link multiple traces from the same conversation
    or process. For example, you might use a chat thread ID.
    """

    trace_metadata: dict[str, Any] | None = None
    """
    An optional dictionary of additional metadata to include with the trace.
    """


class RestateRunner:
    @classmethod
    async def run(
            cls,
            starting_agent: Agent[restate.ObjectContext],
            input: str | list[TResponseInputItem],
            *,
            context: restate.ObjectContext | None = None,
            max_turns: int = DEFAULT_MAX_TURNS,
            hooks: RunHooks[restate.ObjectContext] | None = None,
            run_config: RunConfig | None = None,
    ) -> RunResult:
        """Run a workflow starting at the given agent. The agent will run in a loop until a final
        output is generated. The loop runs like so:
        1. The agent is invoked with the given input.
        2. If there is a final output (i.e. the agent produces something of type
            `agent.output_type`, the loop terminates.
        3. If there's a handoff, we run the loop again, with the new agent.
        4. Else, we run tool calls (if any), and re-run the loop.

        In two cases, the agent may raise an exception:
        1. If the max_turns is exceeded, a MaxTurnsExceeded exception is raised.
        2. If a guardrail tripwire is triggered, a GuardrailTripwireTriggered exception is raised.

        Note that only the first agent's input guardrails are run.

        Args:
            starting_agent: The starting agent to run.
            input: The initial input to the agent. You can pass a single string for a user message,
                or a list of input items.
            context: The context to run the agent with.
            max_turns: The maximum number of turns to run the agent for. A turn is defined as one
                AI invocation (including any tool calls that might occur).
            hooks: An object that receives callbacks on various lifecycle events.
            run_config: Global settings for the entire agent run.

        Returns:
            A run result containing all the inputs, guardrail results and the output of the last
            agent. Agents may perform handoffs, so we don't know the specific type of the output.
        """
        if hooks is None:
            hooks = RunHooks[Any]()
        if run_config is None:
            run_config = RunConfig()

        with TraceCtxManager(
                workflow_name=run_config.workflow_name,
                trace_id=run_config.trace_id,
                group_id=run_config.group_id,
                metadata=run_config.trace_metadata,
                disabled=run_config.tracing_disabled,
        ):
            current_turn = 0
            original_input: str | list[TResponseInputItem] = copy.deepcopy(input)
            generated_items: list[RunItem] = []
            model_responses: list[ModelResponse] = []

            context_wrapper: RunContextWrapper[restate.ObjectContext] = RunContextWrapper(
                context=context,  # type: ignore
            )

            input_guardrail_results: list[InputGuardrailResult] = []

            current_span: Span[AgentSpanData] | None = None
            current_agent = starting_agent
            should_run_agent_start_hooks = True

            try:
                while True:
                    # Start an agent span if we don't have one. This span is ended if the current
                    # agent changes, or if the agent loop ends.
                    if current_span is None:
                        handoff_names = [h.agent_name for h in cls._get_handoffs(current_agent)]
                        tool_names = [t.name for t in current_agent.tools]
                        if output_schema := cls._get_output_schema(current_agent):
                            output_type_name = output_schema.output_type_name()
                        else:
                            output_type_name = "str"

                        current_span = agent_span(
                            name=current_agent.name,
                            handoffs=handoff_names,
                            tools=tool_names,
                            output_type=output_type_name,
                        )
                        current_span.start(mark_as_current=True)

                    current_turn += 1
                    if current_turn > max_turns:
                        _utils.attach_error_to_span(
                            current_span,
                            SpanError(
                                message="Max turns exceeded",
                                data={"max_turns": max_turns},
                            ),
                        )
                        raise TerminalError(f"MaxTurnExceeded: Max turns ({max_turns}) exceeded")

                    logging.debug(
                        f"Running agent {current_agent.name} (turn {current_turn})",
                    )

                    # TODO
                    # if current_turn == 1:
                    #     input_guardrail_results, turn_result = await asyncio.gather(
                    #         cls._run_input_guardrails(
                    #             starting_agent,
                    #             starting_agent.input_guardrails
                    #             + (run_config.input_guardrails or []),
                    #             copy.deepcopy(input),
                    #             context_wrapper,
                    #             ),
                    #         cls._run_single_turn(
                    #             agent=current_agent,
                    #             original_input=original_input,
                    #             generated_items=generated_items,
                    #             hooks=hooks,
                    #             context_wrapper=context_wrapper,
                    #             run_config=run_config,
                    #             should_run_agent_start_hooks=should_run_agent_start_hooks,
                    #         ),
                    #     )
                    # else:
                    turn_result = await cls._run_single_turn(
                        agent=current_agent,
                        original_input=original_input,
                        generated_items=generated_items,
                        hooks=hooks,
                        context_wrapper=context_wrapper,
                        run_config=run_config,
                        should_run_agent_start_hooks=should_run_agent_start_hooks,
                    )
                    should_run_agent_start_hooks = False

                    model_responses.append(turn_result.model_response)
                    original_input = turn_result.original_input
                    generated_items = turn_result.generated_items

                    if isinstance(turn_result.next_step, NextStepFinalOutput):
                        async def run_output_guardrails():
                            return await cls._run_output_guardrails(
                                current_agent.output_guardrails + (run_config.output_guardrails or []),
                                current_agent,
                                turn_result.next_step.output,
                                context_wrapper,
                            )

                        output_guardrail_results = await context.run("Output guardrails", run_output_guardrails)
                        return RunResult(
                            input=original_input,
                            new_items=generated_items,
                            raw_responses=model_responses,
                            final_output=turn_result.next_step.output,
                            _last_agent=current_agent,
                            input_guardrail_results=input_guardrail_results,
                            output_guardrail_results=output_guardrail_results,
                        )
                    elif isinstance(turn_result.next_step, NextStepHandoff):
                        current_agent = cast(Agent[restate.ObjectContext], turn_result.next_step.new_agent)
                        current_span.finish(reset_current=True)
                        current_span = None
                        should_run_agent_start_hooks = True
                    elif isinstance(turn_result.next_step, NextStepRunAgain):
                        pass
                    else:
                        raise AgentsException(
                            f"Unknown next step type: {type(turn_result.next_step)}"
                        )
            finally:
                if current_span:
                    current_span.finish(reset_current=True)

    @classmethod
    async def _run_single_turn(
            cls,
            *,
            agent: Agent[restate.ObjectContext],
            original_input: str | list[TResponseInputItem],
            generated_items: list[RunItem],
            hooks: RunHooks[restate.ObjectContext],
            context_wrapper: RunContextWrapper[restate.ObjectContext],
            run_config: RunConfig,
            should_run_agent_start_hooks: bool,
    ) -> SingleStepResult:
        # Ensure we run the hooks before anything else
        if should_run_agent_start_hooks:
            await asyncio.gather(
                hooks.on_agent_start(context_wrapper, agent),
                (
                    agent.hooks.on_start(context_wrapper, agent)
                    if agent.hooks
                    else _utils.noop_coroutine()
                ),
            )

        system_prompt = await agent.get_system_prompt(context_wrapper)

        output_schema = cls._get_output_schema(agent)
        handoffs = cls._get_handoffs(agent)
        input = ItemHelpers.input_to_new_input_list(original_input)
        input.extend([generated_item.to_input_item() for generated_item in generated_items])

        new_response = await cls._get_new_response(
            agent,
            system_prompt,
            input,
            output_schema,
            handoffs,
            context_wrapper,
            run_config,
        )

        return await cls._get_single_step_result_from_response(
            agent=agent,
            original_input=original_input,
            pre_step_items=generated_items,
            new_response=new_response,
            output_schema=output_schema,
            handoffs=handoffs,
            hooks=hooks,
            context_wrapper=context_wrapper,
            run_config=run_config,
        )

    @classmethod
    async def _get_single_step_result_from_response(
            cls,
            *,
            agent: Agent[restate.ObjectContext],
            original_input: str | list[TResponseInputItem],
            pre_step_items: list[RunItem],
            new_response: ModelResponse,
            output_schema: AgentOutputSchema | None,
            handoffs: list[Handoff],
            hooks: RunHooks[restate.ObjectContext],
            context_wrapper: RunContextWrapper[restate.ObjectContext],
            run_config: RunConfig,
    ) -> SingleStepResult:
        processed_response = RunImpl.process_model_response(
            agent=agent,
            response=new_response,
            output_schema=output_schema,
            handoffs=handoffs,
        )
        return await RunImpl.execute_tools_and_side_effects(
            agent=agent,
            original_input=original_input,
            pre_step_items=pre_step_items,
            new_response=new_response,
            processed_response=processed_response,
            output_schema=output_schema,
            hooks=hooks,
            context_wrapper=context_wrapper,
            run_config=run_config,
        )

    @classmethod
    async def _run_input_guardrails(
            cls,
            agent: Agent[Any],
            guardrails: list[InputGuardrail[restate.ObjectContext]],
            input: str | list[TResponseInputItem],
            context: RunContextWrapper[restate.ObjectContext],
    ) -> list[InputGuardrailResult]:
        if not guardrails:
            return []

        guardrail_tasks = [
            asyncio.create_task(
                RunImpl.run_single_input_guardrail(agent, guardrail, input, context)
            )
            for guardrail in guardrails
        ]

        guardrail_results = []

        for done in asyncio.as_completed(guardrail_tasks):
            result = await done
            if result.output.tripwire_triggered:
                # Cancel all guardrail tasks if a tripwire is triggered.
                for t in guardrail_tasks:
                    t.cancel()
                _utils.attach_error_to_current_span(
                    SpanError(
                        message="Guardrail tripwire triggered",
                        data={"guardrail": result.guardrail.get_name()},
                    )
                )
                raise InputGuardrailTripwireTriggered(result)
            else:
                guardrail_results.append(result)

        return guardrail_results

    @classmethod
    async def _run_output_guardrails(
            cls,
            guardrails: list[OutputGuardrail[restate.ObjectContext]],
            agent: Agent[restate.ObjectContext],
            agent_output: Any,
            context: RunContextWrapper[restate.ObjectContext],
    ) -> list[OutputGuardrailResult]:
        if not guardrails:
            return []

        guardrail_tasks = [
            asyncio.create_task(
                RunImpl.run_single_output_guardrail(guardrail, agent, agent_output, context)
            )
            for guardrail in guardrails
        ]

        guardrail_results = []

        for done in asyncio.as_completed(guardrail_tasks):
            result = await done
            if result.output.tripwire_triggered:
                # Cancel all guardrail tasks if a tripwire is triggered.
                for t in guardrail_tasks:
                    t.cancel()
                _utils.attach_error_to_current_span(
                    SpanError(
                        message="Guardrail tripwire triggered",
                        data={"guardrail": result.guardrail.get_name()},
                    )
                )
                raise OutputGuardrailTripwireTriggered(result)
            else:
                guardrail_results.append(result)

        return guardrail_results

    @classmethod
    async def _get_new_response(
            cls,
            agent: Agent[restate.ObjectContext],
            system_prompt: str | None,
            input: list[TResponseInputItem],
            output_schema: AgentOutputSchema | None,
            handoffs: list[Handoff],
            context_wrapper: RunContextWrapper[restate.ObjectContext],
            run_config: RunConfig,
    ) -> ModelResponse:
        model = cls._get_model(agent, run_config)
        model_settings = agent.model_settings.resolve(run_config.model_settings)

        async def get_model_response() -> Dict[str, Any]:
            resp = await model.get_response(
                system_instructions=system_prompt,
                input=input,
                model_settings=model_settings,
                tools=agent.tools,
                output_schema=output_schema,
                handoffs=handoffs,
                tracing=get_model_tracing_impl(
                    run_config.tracing_disabled, run_config.trace_include_sensitive_data
                ),
            )
            return serialize_model_response(resp)

        dict_response = await context_wrapper.context.run("LLM call - "+ agent.name, get_model_response)
        new_response: ModelResponse = deserialize_model_response(dict_response)
        context_wrapper.usage.add(new_response.usage)

        return new_response

    @classmethod
    def _get_output_schema(cls, agent: Agent[Any]) -> AgentOutputSchema | None:
        if agent.output_type is None or agent.output_type is str:
            return None

        return AgentOutputSchema(agent.output_type)

    @classmethod
    def _get_handoffs(cls, agent: Agent[Any]) -> list[Handoff]:
        handoffs = []
        for handoff_item in agent.handoffs:
            if isinstance(handoff_item, Handoff):
                handoffs.append(handoff_item)
            elif isinstance(handoff_item, Agent):
                handoffs.append(handoff(handoff_item))
        return handoffs

    @classmethod
    def _get_model(cls, agent: Agent[Any], run_config: RunConfig) -> Model:
        if isinstance(run_config.model, Model):
            return run_config.model
        elif isinstance(run_config.model, str):
            return run_config.model_provider.get_model(run_config.model)
        elif isinstance(agent.model, Model):
            return agent.model

        return run_config.model_provider.get_model(agent.model)



# ---------------------------------------------------------------------------
# Model response serializer


def serialize_model_response(response: ModelResponse) -> Dict[str, Any]:
    """
    Serializes a ModelResponse object to a dictionary that can be JSON serialized.

    Args:
        response: The ModelResponse object to serialize

    Returns:
        A dictionary representation of the ModelResponse
    """
    return {
        "output": [output.model_dump(exclude_unset=True) for output in response.output],
        "usage": {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            "total_tokens": response.usage.total_tokens
        },
        "referenceable_id": response.referenceable_id
    }

def serialize_model_response_to_json(response: ModelResponse) -> str:
    """
    Serializes a ModelResponse object to a JSON string.

    Args:
        response: The ModelResponse object to serialize

    Returns:
        A JSON string representation of the ModelResponse
    """
    return json.dumps(serialize_model_response(response))


def deserialize_model_response(data: Dict[str, Any]) -> ModelResponse:
    """
    Deserializes a dictionary into a ModelResponse object.

    Args:
        data: The dictionary containing serialized ModelResponse data

    Returns:
        A ModelResponse object
    """

    # First, convert the plain dictionaries to their corresponding Pydantic models
    output_items = []
    for item_dict in data["output"]:
        if item_dict.get("type") == "message":
            # Process content for message items
            content_list = []
            for content_item in item_dict.get("content", []):
                if content_item.get("type") == "output_text":
                    content_list.append(ResponseOutputText(type="output_text", text=content_item["text"], annotations=content_item.get("annotations")))
                elif content_item.get("type") == "refusal":
                    content_list.append(ResponseOutputRefusal(type="refusal", refusal=content_item["refusal"]))

            output_items.append(ResponseOutputMessage(
                id=item_dict.get("id"),
                type="message",
                role=item_dict.get("role", "assistant"),
                content=content_list,
                status=item_dict.get("status")
            ))
        elif item_dict.get("type") == "function_call":
            output_items.append(ResponseFunctionToolCall(**item_dict))
        elif item_dict.get("type") == "computer_call":
            output_items.append(ResponseComputerToolCall(**item_dict))
        elif item_dict.get("type") == "file_search_call":
            output_items.append(ResponseFileSearchToolCall(**item_dict))
        elif item_dict.get("type") == "web_search_call":
            output_items.append(ResponseFunctionWebSearch(**item_dict))

    # Create the Usage object
    usage_data = data.get("usage", {})
    usage = Usage(
        input_tokens=usage_data.get("input_tokens", 0),
        output_tokens=usage_data.get("output_tokens", 0),
        total_tokens=usage_data.get("total_tokens", 0)
    )

    # Create and return the ModelResponse
    return ModelResponse(
        output=output_items,
        usage=usage,
        referenceable_id=data.get("referenceable_id")
    )


def deserialize_model_response_from_json(json_str: str) -> ModelResponse:
    """
    Deserializes a JSON string into a ModelResponse object.

    Args:
        json_str: The JSON string containing serialized ModelResponse data

    Returns:
        A ModelResponse object
    """
    data = json.loads(json_str)
    return deserialize_model_response(data)