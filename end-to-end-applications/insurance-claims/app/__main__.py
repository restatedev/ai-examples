import hypercorn
import asyncio
import restate
import logging

from workflow import claim_workflow


def setup_logging():
    """
    Set up logging configuration.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] [%(process)d] [%(levelname)s] - %(message)s",
    )


def main():
    setup_logging()

    app = restate.app(services=[claim_workflow])

    conf = hypercorn.Config()
    conf.bind = ["0.0.0.0:9080"]
    asyncio.run(hypercorn.asyncio.serve(app, conf))


if __name__ == "__main__":
    main()
