import hypercorn
import asyncio
import restate

from chat_session import agent_session

app = restate.app(services=[agent_session])

if __name__ == "__main__":
    conf = hypercorn.Config()
    conf.bind = ["0.0.0.0:9081"]
    asyncio.run(hypercorn.asyncio.serve(app, conf))
