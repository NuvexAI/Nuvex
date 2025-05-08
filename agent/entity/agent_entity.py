import time
import uuid
from typing import Optional, Any, List, Union, Literal

from pydantic import BaseModel, Field

from agents.utils.common import get_current_time


class ChatMsgResp(BaseModel):
    role: str = Field(..., description="The role of the message")
    content: str = None


class ChatRespChoice(BaseModel):
    index: int = Field(..., description="The index of the choice.")
    input: str = Field(..., description="The input message.")
    message: ChatMsgResp = Field(
        ..., description="The output message."
    )


class AgentChatResp(BaseModel):
    id: Optional[str] = Field(
        f"deepcore-agent--{uuid.uuid4().hex}",
        description="The ID of the agent that generated the completion response.",
    )
    agent_name: Optional[str] = Field(
        ...,
        description="The name of the agent that generated the completion response.",
    )
    object: Optional[
        Literal["chat.completion", "chat.completion.chunk"]
    ] = None
    choices: Optional[ChatRespChoice] = None
    created: Optional[int] = Field(
        default_factory=lambda: int(time.time())
    )


class Step(BaseModel):
    step_id: Optional[str] = Field(
        default_factory=lambda: uuid.uuid4().hex,
        description="The ID of the task step.",
        examples=["6bb1801a-fd80-45e8-899a-4dd723cc602e"],
    )
    time: Optional[float] = Field(
        default_factory=get_current_time,
        description="The time taken to complete the task step.",
    )
    response: Optional[AgentChatResp]


class DeepAgentExecutorOutput(BaseModel):
    agent_id: Optional[str] = Field(
        ...,
        description="The ID of the agent.",
    )
    agent_name: Optional[str] = Field(
        ...,
        description="The ID of the agent.",
    )
    task: Optional[str] = Field(
        ...,
        description="The name of the task.",
    )
    max_loops: Optional[Any] = Field(
        ...,
        description="The number of steps in the task.",
    )
    steps: Optional[List[Union[Step, Any]]] = Field(
        [],
        description="The steps of the task.",
    )
    full_history: Optional[str] = Field(
        ...,
        description="The full history of the task.",
    )
    total_tokens: Optional[int] = Field(
        ...,
        description="The total number of tokens generated.",
    )
