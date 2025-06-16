import hypercorn
import asyncio
import restate
import logging

from agent import agent
from utils.account import account

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(process)d] [%(levelname)s] - %(message)s",
)


def main():
    app = restate.app(
        services=[
            agent,
            account,
        ]
    )

    conf = hypercorn.Config()
    conf.bind = ["0.0.0.0:9080"]
    asyncio.run(hypercorn.asyncio.serve(app, conf))


if __name__ == "__main__":
    main()
