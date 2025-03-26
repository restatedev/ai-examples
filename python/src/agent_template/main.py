import hypercorn
import asyncio
import restate

from chat_session import chat_service
from services.faq_service import faq_service
from services.booking_object import booking_object
from services.seat_object import seat_object

app = restate.app(services=[chat_service, faq_service, booking_object, seat_object])

if __name__ == "__main__":
    conf = hypercorn.Config()
    conf.bind = ["0.0.0.0:9080"]
    asyncio.run(hypercorn.asyncio.serve(app, conf))
