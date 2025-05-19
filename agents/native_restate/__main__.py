import hypercorn
import asyncio
import restate

from agent import agent
from account import account


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
