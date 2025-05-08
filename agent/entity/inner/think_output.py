from agents.agent.entity.inner.inner_output import Output
from agents.agent.tools.message_tool import send_message


class ThinkOutput(Output):
    data = {}

    def __init__(self, data: dict = None):
        self.data = data or {"type": "message"}

    def write_text(self, text):
        self.data["text"] = text
        return self

    def to_stream(self) -> str:
        return send_message("think",  self.data)
        
    @staticmethod
    def create_from_chunk(chunk: str) -> 'ThinkOutput':
        return ThinkOutput().write_text(chunk)

    def get_response(self) -> str:
        return ""
