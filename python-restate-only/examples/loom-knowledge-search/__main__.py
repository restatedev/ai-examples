import asyncio
import os
from typing import TypedDict

import httpx
import restate
from hypercorn.asyncio import serve
from hypercorn.config import Config


class SearchRequest(TypedDict):
    query: str


class Excerpt(TypedDict):
    source_uri: str
    content: str


async def search_loom(query: str) -> list[Excerpt]:
    base_url = os.environ["LOOM_BASE_URL"].rstrip("/")
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(
            f"{base_url}/v1/knowledge.search",
            headers={"Authorization": f"Bearer {os.environ['LOOM_TOKEN']}"},
            json={
                "org": os.environ["LOOM_ORG"],
                "namespace": os.environ["LOOM_NAMESPACE"],
                "namespace_scope": "this",
                "query": query,
                "top_k": 3,
                "search_mode": "lexical",
                "rerank": "none",
            },
        )
        if 400 <= response.status_code < 500 and response.status_code not in (408, 429):
            raise restate.TerminalError(f"Loom search returned HTTP {response.status_code}")
        response.raise_for_status()

    return [
        {"source_uri": hit["source_uri"], "content": hit["content"]}
        for hit in response.json()["results"]
    ]


search_service = restate.Service("LoomKnowledge")


@search_service.handler()
async def search(ctx: restate.Context, request: SearchRequest) -> list[Excerpt]:
    return await ctx.run_typed(
        "Search runbooks", search_loom, restate.RunOptions(max_attempts=3), request["query"]
    )


if __name__ == "__main__":
    config = Config()
    config.bind = ["127.0.0.1:9080"]
    asyncio.run(serve(restate.app(services=[search_service]), config))
