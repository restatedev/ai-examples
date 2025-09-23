import json
import restate
import logging

from datetime import timedelta
from openai import OpenAI
from openai.types.responses import Response, ResponseFunctionToolCall, FunctionToolParam
from pydantic import BaseModel

from utils.models import AgentResponse, AgentInput

logger = logging.getLogger(__name__)

client = OpenAI()


class Task(BaseModel):
    """
    The task that needs to get executed

    Args:
        description (str): The description of the task to execute.
    """

    description: str

    class Config:
        extra = "forbid"


agent = restate.VirtualObject("Agent")

NEW_INPUT_PROMISE = "new_input_promise"


@agent.handler()
async def run(ctx: restate.ObjectContext, req: AgentInput):
    input_items = [{"role": "user", "content": msg} for msg in req.message_history]
    logger.info("Starting new agent run with input: %s", input_items)

    id, new_input_promise = ctx.awakeable(type_hint=str)
    ctx.set(NEW_INPUT_PROMISE, id)

    # run agent loop
    while True:
        # call agent
        response = await ctx.run_typed("Call agent", call_task_agent, input_items=input_items)
        output = response.output[0]
        logger.info(f"Agent generated output: {output}")

        # run tools
        if isinstance(output, ResponseFunctionToolCall):
            task = Task(**json.loads(output.arguments))
            task_result = await execute_task(ctx, task)
            input_items.append({"role": "system", "content": task_result})

        # peek for new input
        match await restate.select(
            new_input_promise=new_input_promise, timeout=ctx.sleep(timedelta(seconds=0))
        ):
            case ["new_input_promise", new_input]:
                logger.info(f"Incorporating new input for {ctx.key()}: {new_input}")
                id, new_input_promise = ctx.awakeable()
                ctx.set(NEW_INPUT_PROMISE, id)

                # incorporate new input
                input_items.append({"role": "user", "content": new_input})

                # always do another iteration; also when the agent already generated output
                continue

        # process final response
        if response.output_text != "":
            logger.info(f"Final output message: {response.output_text}")
            from chat import process_agent_response

            ctx.object_send(
                process_agent_response,
                key=ctx.key(),
                arg=AgentResponse(final_output=response.output_text),
            )
            ctx.clear(NEW_INPUT_PROMISE)
            return


@agent.handler(kind="shared")
async def incorporate_new_input(ctx: restate.ObjectSharedContext, req: str) -> bool:
    id = await ctx.get(NEW_INPUT_PROMISE, type_hint=str)

    if id is None:
        logger.warning(
            f"No awakeable ID found. Maybe invocation finished in the meantime. Cannot incorporate new input for {ctx.key()}."
        )
        return False

    ctx.resolve_awakeable(id, req)
    logger.info(
        f"Resolved awakeable with ID {id} with new input for {ctx.key()}: {req}"
    )
    return True


# UTILS


async def execute_task(ctx: restate.ObjectContext, req: Task) -> str:
    """
    Executes tasks, based on the description provided.

    Args:
        task (Task): The task to execute.
    """
    logger.info("Executing a slow task with description: %s...", req.description)

    await ctx.sleep(timedelta(seconds=5))
    return f"Task executed successfully: {req.description}"


execute_task_tool = FunctionToolParam(
    name=execute_task.__name__,
    description=execute_task.__doc__,
    parameters=Task.model_json_schema(),
    strict=True,
    type="function",
)


async def call_task_agent(input_items) -> Response:
    return client.responses.create(
        model="gpt-4o",
        instructions="""
        You are a helpful task agent. You use the `execute_task` tool to execute a task for the user.
        If the user specifies multiple tasks then execute them one by one. 
        """,
        input=input_items,
        tools=[execute_task_tool],
        parallel_tool_calls=False,
        stream=False,
    )
