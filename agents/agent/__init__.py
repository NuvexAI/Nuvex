from abc import ABC


class AbstractAgent(ABC):
    stop_condition = ["Final Answer:", "Tool Clarify:"]
    default_final_answer = "Sorry, I can't help with that. Try rephrasing or asking a related question for better results!"

    async def stream(self, query: str, conversation_id: str):
        raise NotImplementedError("arun is not implemented")
