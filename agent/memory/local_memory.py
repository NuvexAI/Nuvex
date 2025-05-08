from agents.agent.memory.memory import MemoryStore, MemoryObject


class LocalMemoryStore(MemoryStore):
    memory: dict[str, list[MemoryObject]] = {}

    def __init__(self, memory_size: int = 10) -> None:
        super().__init__(memory_size=memory_size)

    def get_memory_by_conversation_id(self, conversation_id: str) -> list[MemoryObject]:
        return self.memory.get(conversation_id, [])

    def save_memory(self, conversation_id: str, memory: MemoryObject):
        if conversation_id not in self.memory:
            self.memory[conversation_id] = []
        if len(self.memory[conversation_id]) >= self.memory_size:
            del self.memory[conversation_id][0]
        self.memory[conversation_id].append(memory)


local_memory = LocalMemoryStore()
