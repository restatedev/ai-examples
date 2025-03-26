import logging

import restate

from chat_session import chat_service, faq_service

app = restate.app(services=[
    chat_service,
    faq_service
])
