import hypercorn
import asyncio
import restate

from chat import chat_service
from agent import agent
import logging

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(name)s: %(message)s',
)

def main():
    app = restate.app(
        services=[
            chat_service,
            agent,
        ]
    )

    conf = hypercorn.Config()
    conf.bind = ["0.0.0.0:9080"]
    asyncio.run(hypercorn.asyncio.serve(app, conf))


if __name__ == "__main__":
    main()
