import hypercorn
import asyncio
import restate

from agent import mcp_service

app = restate.app(
    services=[
        mcp_service,
    ]
)

conf = hypercorn.Config()
conf.bind = ["0.0.0.0:9080"]
asyncio.run(hypercorn.asyncio.serve(app, conf))
