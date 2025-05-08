import json
from abc import ABC
from datetime import datetime
from typing import Union, Optional, Dict


class MemoryObject:
    input: str
    output: Union[str, dict]
    time: datetime

    def __init__(self,
                 input: str = None,
                 output: Union[str, dict] = None,
                 time: Optional[datetime] = None,
                 temp_data: Optional[Dict] = None):
        self.input = input
        self.output = output
        self.time = time
        self.temp_data = temp_data

    def get_input(self) -> str:
        return self.input

    def get_output_to_string(self) -> str:
        if isinstance(self.output, str):
            return self.output
        else:
            return json.dumps(self.output, ensure_ascii=False)

    def to_dict(self) -> dict:
        return {
            "input": self.get_input(),
            "output": self.get_output_to_string(),
            "time": self.time,
            "temp_data": self.temp_data
        }

    @staticmethod
    def from_dict(data: dict):
        self = MemoryObject()
        self.input = data.get("input", "")
        self.output = data.get("output", "")
        self.time = data.get("time", None)
        self.temp_data = data.get("temp_data", None)
        return self


class MemoryStore(ABC):
    memory_size: int = 10

    def __init__(self, memory_size: int = 10):
        self.memory_size = memory_size

    def get_memory_by_conversation_id(self, conversation_id: str) -> list[MemoryObject]:
        pass

    def save_memory(self, conversation_id: str, memory: MemoryObject):
        pass
