# Restate + LangChain examples (Python)

Resilient AI agents built with [LangChain `create_agent`](https://docs.langchain.com/oss/python/langchain/agents) and [Restate](https://restate.dev/).

The integration is a single `RestateMiddleware` you attach to `create_agent`. It journals every LLM call, and serializes parallel tool executions via a turnstile so any `ctx.run_typed` calls inside tool bodies replay deterministically.

## Examples

- **[template/](template)** — minimal weather agent. Start here.
- **[tour-of-agents/](tour-of-agents)** — twelve patterns: durable sessions, HITL, multi-agent, parallel tools, sub-workflows, remote agents, sequential / parallel / orchestrator / evaluator workflows, error handling.

## Pattern

```python
from langchain.agents import create_agent
from restate.ext.langchain import RestateMiddleware, restate_context

agent = create_agent(
    model=init_chat_model("openai:gpt-4o-mini"),
    tools=[my_tool],
    middleware=[RestateMiddleware()],
)

@service.handler()
async def chat(ctx: restate.Context, msg: str) -> str:
    result = await agent.ainvoke({"messages": [{"role": "user", "content": msg}]})
    return result["messages"][-1].content
```

Inside tools, wrap side effects you want durable in `restate_context().run_typed("name", ...)`. The middleware does NOT auto-journal tool calls — you choose which steps are durable.
