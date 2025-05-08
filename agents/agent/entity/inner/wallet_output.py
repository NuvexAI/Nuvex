import json

from agents.agent.entity.inner.inner_output import Output
from agents.agent.tools.message_tool import send_message


class WalletOutput(Output):
    data: dict = None

    def __init__(self, data: dict = None):
        self.data = data or {}

    def add_value(self, key, value):
        self.data[key] = value

    def to_stream(self) -> str:
        return send_message("wallet", self.data)

    def get_response(self) -> str:
        return json.dumps(self.data, ensure_ascii=False)
