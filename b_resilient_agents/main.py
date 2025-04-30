import hypercorn
import asyncio
import restate

from .chat import chat_service

def main():
    app = restate.app(services=[chat_service])

    conf = hypercorn.Config()
    conf.bind = ["0.0.0.0:9080"]
    asyncio.run(hypercorn.asyncio.serve(app, conf))

if __name__ == "__main__":
    main()
