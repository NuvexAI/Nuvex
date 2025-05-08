from abc import ABC


class Output(ABC):

    def to_stream(self) -> str:
        pass

    def get_response(self) -> str:
        pass
