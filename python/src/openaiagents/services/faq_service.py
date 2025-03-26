from __future__ import annotations as _annotations

import restate

from pydantic import BaseModel


faq_service = restate.Service("FaqAgent")


class LookupRequest(BaseModel):
    """
    A request to the faq_lookup_tool.
    This request is the input for the tool with name: faq_lookup_tool
    The question parameter is the question that the tool will answer.
    """

    question: str


@faq_service.handler()
async def faq_lookup_tool(ctx: restate.Context, question: LookupRequest) -> str:
    if "bag" in question or "baggage" in question:
        return (
            "You are allowed to bring one bag on the plane. "
            "It must be under 50 pounds and 22 inches x 14 inches x 9 inches."
        )
    elif "seats" in question or "plane" in question:
        return (
            "There are 120 seats on the plane. "
            "There are 22 business class seats and 98 economy seats. "
            "Exit rows are rows 4 and 16. "
            "Rows 5-8 are Economy Plus, with extra legroom. "
        )
    elif "wifi" in question:
        return "We have free wifi on the plane, join Airline-Wifi"
    return "I'm sorry, I don't know the answer to that question."
