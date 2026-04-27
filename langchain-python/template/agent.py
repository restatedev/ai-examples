from datetime import timedelta

import restate
from langchain.agents import create_agent
from langchain_core.messages import AnyMessage
from langchain_core.tools import tool
from langchain.chat_models import init_chat_model
from pydantic import BaseModel

from restate.ext.langchain import RestateMiddleware, PydanticTypeAdapter, restate_context

MESSAGES_SERDE = PydanticTypeAdapter(list[AnyMessage])


class WeatherPrompt(BaseModel):
    message: str = "What is the weather in San Francisco?"


# TOOL
@tool
async def get_weather(city: str) -> dict:
    """Get the current weather for a given city."""

    async def call_weather_api() -> dict:
        return {"temperature": 23, "description": "Sunny and warm."}

    # Durable step: results are journaled, so on retry we replay the value
    # rather than re-hitting the API.
    return await restate_context().run_typed(f"Get weather {city}", call_weather_api)


# AGENT
weather_agent = create_agent(
    model=init_chat_model("openai:gpt-4o-mini"),
    tools=[get_weather],
    system_prompt="You are a helpful agent that provides weather updates.",
    middleware=[RestateMiddleware()],
)


# AGENT SERVICE
agent_service = restate.Service("agent")


@agent_service.handler()
async def run(_ctx: restate.Context, req: WeatherPrompt) -> str:
    result = await weather_agent.ainvoke({"messages": [{"role": "user", "content": req.message}]})
    return result["messages"][-1].content
