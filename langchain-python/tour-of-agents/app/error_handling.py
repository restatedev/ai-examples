"""Tool retries and TerminalError handling.

Wrap fragile side effects in `restate_context().run_typed(...)` with retry
options. Once `max_attempts` is exhausted, the run raises `TerminalError`
which propagates up past LangChain's tool-error handling and back to the
service handler."""

from datetime import timedelta

import restate
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain_core.tools import tool

from restate.ext.langchain import RestateMiddleware, restate_context

from utils.models import WeatherPrompt, WeatherRequest, WeatherResponse
from utils.utils import fetch_weather


# <start_here>
@tool
async def get_weather(city: WeatherRequest) -> WeatherResponse:
    """Get the current weather for a given city."""
    return await restate_context().run_typed(
        "get weather",
        fetch_weather,
        restate.RunOptions(
            max_attempts=3,
            initial_retry_interval=timedelta(seconds=2),
        ),
        req=city,
    )


# <end_here>


agent = create_agent(
    model=init_chat_model("openai:gpt-5.4"),
    tools=[get_weather],
    system_prompt="You are a helpful agent that provides weather updates.",
    middleware=[RestateMiddleware()],
)


agent_service = restate.Service("WeatherAgent")


@agent_service.handler()
async def run(_ctx: restate.Context, req: WeatherPrompt) -> str:
    # <start_handle>
    try:
        result = await agent.ainvoke(
            {"messages": [{"role": "user", "content": req.message}]}
        )
    except restate.TerminalError as e:
        return f"The agent couldn't complete the request: {e.message}"
    # <end_handle>

    return result["messages"][-1].content


if __name__ == "__main__":
    import asyncio

    import hypercorn
    import hypercorn.asyncio

    app = restate.app(services=[agent_service])
    conf = hypercorn.Config()
    conf.bind = ["0.0.0.0:9080"]
    asyncio.run(hypercorn.asyncio.serve(app, conf))
