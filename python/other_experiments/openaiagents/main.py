import restate

from src.openaiagents.services.seat_object import seat_object
from src.openaiagents.services.booking_object import booking_object
from src.openaiagents.services.faq_service import faq_service
from chat_session import chat_service

app = restate.app(services=[chat_service, booking_object, faq_service, seat_object])
