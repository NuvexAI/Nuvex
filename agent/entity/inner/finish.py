from agents.agent.entity.inner.inner_output import Output


class FinishOutput(Output):

    def to_stream(self) -> str:
        pass

    def get_response(self) -> str:
        pass