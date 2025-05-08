"""NodeMessage Class"""
from typing import Optional

from agents.agent.entity.inner.inner_output import Output
from agents.agent.tools.message_tool import send_message


class NodeMessage(Output):
    message: str = ""
    tool_name: str = ""

    def __init__(self, message: str, tool_name: Optional[str] = None):
        """Constructor for the class"""
        self.message = message
        self.tool_name = tool_name

    def to_dict(self):
        data = {}
        for key, value in self.__dict__.items():
            if value:
                data[key] = value
        return data

    def to_stream(self) -> str:
        return send_message("status", self.to_dict())

    def get_response(self) -> str:
        return ""


