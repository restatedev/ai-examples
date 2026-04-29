"""Persistent, isolated agent sessions backed by a Virtual Object.

Each Virtual Object key (e.g. a `chat_id`) is a single-writer thread whose
conversation history is stored in Restate's K/V store and survives crashes,
restarts, and concurrent calls."""

import restate
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain_core.messages import AnyMessage, HumanMessage
from pydantic import BaseModel, Field

from restate.ext.langchain import RestateMiddleware

from utils.models import ChatMessage


class ChatHistory(BaseModel):
    messages: list[AnyMessage] = Field(default_factory=list)


# <start_here>
chat = restate.VirtualObject("Chat")

agent = create_agent(
    model=init_chat_model("openai:gpt-5.4"),
    system_prompt="You are a helpful assistant.",
    middleware=[RestateMiddleware()],
)


@chat.handler()
async def message(ctx: restate.ObjectContext, req: ChatMessage) -> str:
    history = await ctx.get("messages", type_hint=ChatHistory) or ChatHistory()
    history.messages.append(HumanMessage(content=req.message))

    result = await agent.ainvoke({"messages": history.messages})

    ctx.set("messages", ChatHistory(messages=result["messages"]))
    return result["messages"][-1].content


@chat.handler(kind="shared")
async def get_history(ctx: restate.ObjectSharedContext) -> ChatHistory:
    return await ctx.get("messages", type_hint=ChatHistory) or ChatHistory()


# <end_here>


if __name__ == "__main__":
    import asyncio

    import hypercorn
    import hypercorn.asyncio

    app = restate.app(services=[chat])
    conf = hypercorn.Config()
    conf.bind = ["0.0.0.0:9080"]
    asyncio.run(hypercorn.asyncio.serve(app, conf))
