from agents.agent.entity.inner.inner_output import Output


class ToolOutput(Output):
    data: str = None

    def __init__(self, data: str):
        self.data = data

    def get_output(self) -> str:
        return self.data

    def to_stream(self) -> str:
        return self.data

    def get_response(self) -> str:
        return self.data

