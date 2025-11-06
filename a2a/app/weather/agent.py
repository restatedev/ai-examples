import restate
from google.genai import types as genai_types
from app.weather.utils import WeatherResponse, WeatherPrompt
from app.weather.utils import fetch_weather
from google.adk.tools.tool_context import ToolContext
from app.common.adk.middleware import durable_model_calls
from app.common.adk.restate_runner import RestateRunner
from app.common.adk.restate_session_service import RestateSessionService
from app.common.adk.restate_tools import restate_tools
from app.common.a2a.models import A2AAgent, AgentInvokeResult

APP_NAME = "agents"

agent_service = restate.VirtualObject("WeatherAgent")


async def get_weather(tool_context: ToolContext, city: str) -> WeatherResponse:
    """Get the current weather for a given city."""
    restate_context = tool_context.session.state["restate_context"]
    return await restate_context.run_typed("Get weather", fetch_weather, city=city)


@agent_service.handler()
async def run(ctx: restate.ObjectContext, prompt: WeatherPrompt) -> str:
    user_id = "user"

    from google.adk.agents.llm_agent import Agent

    agent = Agent(
        model=durable_model_calls(ctx, "gemini-2.5-flash"),
        name="weather_agent",
        description="Agent that provides weather updates for cities.",
        instruction="You are a helpful agent that provides weather updates. Use the get_weather tool to fetch current weather information.",
        tools=restate_tools(get_weather),
    )

    session_service = RestateSessionService(ctx)
    await session_service.create_session(
        app_name=APP_NAME, user_id=user_id, session_id=ctx.key()
    )

    runner = RestateRunner(
        restate_context=ctx,
        agent=agent,
        app_name=APP_NAME,
        session_service=session_service,
    )

    events = runner.run_async(
        user_id=user_id,
        session_id=ctx.key(),
        new_message=genai_types.Content(
            role="user", parts=[genai_types.Part.from_text(text=prompt.message)]
        ),
    )

    final_response = ""
    async for event in events:
        if event.is_final_response() and event.content and event.content.parts:
            final_response = event.content.parts[0].text

    return final_response

class ADKWeatherAgent(A2AAgent):
    async def invoke(
        self, restate_context: restate.ObjectContext, query: str, session_id: str
    ) -> AgentInvokeResult:
        final_output = await restate_context.object_call(run, key=session_id, arg=WeatherPrompt(message=query))
        parts = [{"type": "text", "text": final_output}]
        return AgentInvokeResult(
            parts=parts,
            require_user_input=False,
            is_task_complete=True,
        )
