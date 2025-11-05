import hypercorn
import asyncio
import restate

from app.chat import chat
from app.durable_agent import agent_service


app = restate.app(services=[chat, agent_service])


def main():
    """Entry point for running the app."""
    conf = hypercorn.Config()
    conf.bind = ["0.0.0.0:9081"]
    asyncio.run(hypercorn.asyncio.serve(app, conf))


if __name__ == "__main__":
    main()
