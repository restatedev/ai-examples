import hypercorn
import asyncio
import restate

from agent import agent

if __name__ == "__main__":
    app = restate.app(services=[agent])

    conf = hypercorn.Config()
    conf.bind = ["0.0.0.0:9080"]
    asyncio.run(hypercorn.asyncio.serve(app, conf))
