import typing

from pydantic import BaseModel
import json
import restate
from agents import RunContextWrapper

TToolInput = typing.TypeVar("TToolInput", bound=BaseModel)
TCustomContext = typing.TypeVar("TCustomContext", bound=BaseModel)

class EnrichedContext(typing.TypedDict, typing.Generic[TCustomContext]):
    custom_context: TCustomContext | None
    restate_context: restate.ObjectContext

class EmbeddedRequest(BaseModel, typing.Generic[TToolInput]):
    """
    The agent_name is the name of the agent invoking the tool. You can find the agent name in the agent's input schema.
    The tool_name is the name of the tool to call. You can find the tool name in the tool's input schema.
    The request is the request to the tool.
    """
    agent_name: str
    tool_name: str
    request: TToolInput
    class Config:
        extra = "forbid" #

async def restate_tool_router(context: RunContextWrapper[EnrichedContext[TCustomContext]], req: EmbeddedRequest[TToolInput]) -> str:
    try:
        tool_response = await (context.context["restate_context"]
                               .generic_call(service=req.agent_name,
                                             handler=req.tool_name, 
                                             arg=json.dumps(req.request).encode("utf-8")))
        return tool_response.decode("utf-8")
    except Exception as e:
        return e.add_note("The tool could not be called. Make sure the tool_name is correct and the request is valid.")