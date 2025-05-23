from pydantic import BaseModel, Field


class AgentInput(BaseModel):
    message_history: list[str]


class AgentResponse(BaseModel):
    final_output: str


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatHistory(BaseModel):
    entries: list[ChatMessage] = Field(default_factory=list)
