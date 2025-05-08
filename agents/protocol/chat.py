import uuid
from typing import Optional

from pydantic import BaseModel, Field


class ChatCompletionRequest(BaseModel):
    query: Optional[str] = None
    conversation_id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), alias="conversationId")
