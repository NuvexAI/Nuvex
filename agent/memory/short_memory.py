import datetime
import json
from typing import Optional

import yaml


class ShortMemory(object):

    def __init__(
            self,
            system_prompt: Optional[str] = None,
            user_name: Optional[str] = None,
            *args,
            **kwargs,
    ):
        self.system_prompt = system_prompt
        self.user_name = user_name
        self.conversation_history = []

        if self.system_prompt is not None:
            self.add("System: ", self.system_prompt)

    def add(self, role: str, content: str, *args, **kwargs):
        now = datetime.datetime.now()
        timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
        message = {
            "role": role,
            "content": content,
            "timestamp": timestamp,
        }

        self.conversation_history.append(message)

    def delete(self, index: str):
        self.conversation_history.pop(index)

    def update(self, index: str, role, content):
        self.conversation_history[index] = {
            "role": role,
            "content": content,
        }

    def query(self, index: str):
        return self.conversation_history[index]

    def search(self, keyword: str):
        return [
            msg
            for msg in self.conversation_history
            if keyword in msg["content"]
        ]

    def get_history_as_string(self):
        return "\n".join(
            [
                f"{message['role']}: {message['content']}\n\n" if message['role'] else f"{message['content']}\n\n"
                for message in self.conversation_history
            ]
        )

    def get_str(self):
        return self.get_history_as_string()

    def clear(self):
        self.conversation_history = []

    def to_json(self):
        return json.dumps(self.conversation_history)

    def to_dict(self):
        return self.conversation_history

    def to_yaml(self):
        return yaml.dump(self.conversation_history)
