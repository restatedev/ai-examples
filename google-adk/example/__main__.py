import hypercorn
import asyncio
import restate

from app.agent import agent_service

app = restate.app(services=[agent_service])


def main():
    """Entry point for running the app."""
    conf = hypercorn.Config()
    conf.bind = ["0.0.0.0:9080"]
    asyncio.run(hypercorn.asyncio.serve(app, conf))


if __name__ == "__main__":
    main()
