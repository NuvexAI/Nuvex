from typing import Optional, AsyncIterator, Any

from langchain_core.messages import BaseMessageChunk, HumanMessage, AIMessage, SystemMessage, BaseMessage

from agents.agent.executor.executor import AgentExecutor
from agents.agent.memory.memory import MemoryObject
from agents.models.entity import ChatContext


class PromptAgentExecutor(AgentExecutor):

    def __init__(self,
                 chat_context: ChatContext,
                 name: str,
                 llm: Optional[Any] = None,
                 role_settings: str = "",
                 **kwargs) -> None:
        """
        Initialize a PromptAgentExecutor.
        
        Args:
            name: Name of the agent
            llm: Language model instance
            role_settings: Role configuration
            **kwargs: Additional arguments passed to parent class
        """
        kwargs['system_prompt'] = role_settings
        super().__init__(
            chat_context=chat_context,
            name=name,
            llm=llm,
            role_settings=role_settings,
            **kwargs
        )
        self.conversation: list[BaseMessage] = [SystemMessage(content=role_settings)]

    async def stream(
            self,
            task: Optional[str] = None,
            img: Optional[str] = None,
            *args,
            **kwargs,
    ) -> AsyncIterator[str]:
        self.conversation.append(HumanMessage(content=task))
        async for out in self.llm.astream(self.conversation, *args, **kwargs):
            if isinstance(out, str):
                yield out
            elif isinstance(out, BaseMessageChunk):
                yield out.content

    def add_memory_object(self, memory_list: list[MemoryObject]):
        for memory in memory_list:
            self.conversation.append(HumanMessage(content=memory.input))
            self.conversation.append(AIMessage(content=memory.output))
