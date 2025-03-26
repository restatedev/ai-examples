import hypercorn
import asyncio
import restate

from chat_session import chat_service, faq_service

app = restate.app(services=[
    chat_service,
    faq_service
])

if __name__=="__main__":
    conf = hypercorn.Config()
    conf.bind = ["0.0.0.0:9080"]
    asyncio.run(hypercorn.asyncio.serve(app, conf))

