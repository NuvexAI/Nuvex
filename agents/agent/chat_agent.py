import asyncio
import logging
from datetime import datetime, timezone
from typing import AsyncIterator

from agents.agent import AbstractAgent
from agents.agent.entity.inner.custom_output import CustomOutput
from agents.agent.entity.inner.node_data import NodeMessage
from agents.agent.entity.inner.think_output import ThinkOutput
from agents.agent.entity.inner.tool_output import ToolOutput
from agents.agent.entity.inner.wallet_output import WalletOutput
from agents.agent.executor.agent_executor import DeepAgentExecutor
from agents.agent.factory.agent_factory import AgentExecutorFactory
from agents.agent.llm.custom_llm import CustomChat
from agents.agent.llm.default_llm import openai
from agents.agent.memory.memory import MemoryObject
from agents.agent.memory.redis_memory import RedisMemoryStore
from agents.agent.prompts.tool_prompts import tool_prompt
from agents.agent.tools.function.local_tool_manager import get_local_tool
from agents.agent.tools.message_tool import send_message
from agents.models.entity import AgentInfo, ChatContext
from agents.models.models import App

logger = logging.getLogger(__name__)

class ChatAgent(AbstractAgent):
    """Chat Agent"""

    agent_executor: DeepAgentExecutor = None

    redis_memory: RedisMemoryStore = RedisMemoryStore()

    def __init__(self, app: AgentInfo, chat_context: ChatContext):
        """"
        Initialize the ChatAgent with the given app.
        Args:
            app (App): The application configuration object.
        """
        super().__init__()

        def stopping_condition(response: str):
            for stop_word in self.stop_condition:
                if stop_word in response:
                    return True
            return False

        self.agent_executor = AgentExecutorFactory.create_executor(
            mode=app.mode,
            chat_context=chat_context,
            name=app.name,
            llm=CustomChat(app.model).get_model() if app.model else openai.get_model(),
            api_tools=app.tools,
            local_tools=get_local_tool(),
            tool_system_prompt=app.tool_prompt if app.tool_prompt else tool_prompt(),
            max_loops=app.max_loops if app.max_loops else 5,
            output_type="list",
            node_massage_enabled=True,
            stop_func=stopping_condition,
            # system_prompt=app.description,
            description=app.description,
            role_settings=app.role_settings,
            stop_condition=self.stop_condition,
        )
        self.chat_context: ChatContext = chat_context

    async def stream(self, query: str, conversation_id: str) -> AsyncIterator[str]:
        """
        Run the agent with the given query and conversation ID.
        Args:
            query (str): The user's query or question.
            conversation_id (str): The unique identifier of the conversation.
            init_flag (bool): Flag to indicate if this is an initialization dialogue.
        Returns:
            AsyncIterator[str]: An iterator that yields responses to the user's query.
        """
        current_time = datetime.now(timezone.utc)
        await self.add_memory(conversation_id, current_time)

        response_buffer = ""
        try:
            is_finalized = False
            final_response: list = []
            async for output in self.agent_executor.stream(query):
                if isinstance(output, (NodeMessage, ThinkOutput)):
                    yield output.to_stream()
                    continue
                elif isinstance(output, (ToolOutput, WalletOutput, CustomOutput)):
                    yield output.to_stream()
                    response_buffer += output.get_response() if isinstance(output.get_response(), str) else str(output.get_response())
                    is_finalized = True
                    continue
                elif isinstance(output, list):
                    final_response = output
                    continue
                elif not isinstance(output, str):
                    continue

                response_buffer += output
                is_finalized = True
                if output:
                    yield send_message("message", {"type": "markdown", "text": output})

            # Handle the case where no final response was generated
            if not is_finalized:
                if final_response:
                    response_buffer = final_response[-1]
                    yield send_message("message", {"type": "markdown", "text": final_response[-1]})
                else:
                    yield send_message("message", {"type": "markdown", "text": self.default_final_answer})
        except Exception as e:
            logger.error("stream run failed!", exc_info=True)
            raise e
        finally:
            memory_object = MemoryObject(input=query,
                                         output=response_buffer,
                                         time=current_time,
                                         temp_data=self.chat_context.temp_data)
            self.redis_memory.save_memory(conversation_id, memory_object)
            asyncio.create_task(self.cleanup(conversation_id))
            
    async def cleanup(self, conversation_id: str) -> None:
        """
        Clean up resources associated with a conversation.
        
        Args:
            conversation_id: The unique identifier for the conversation
        """
        # Clear sensitive data from Redis
        if hasattr(self.agent_executor, 'sensitive_data_processor'):
            self.agent_executor.sensitive_data_processor.clear_sensitive_data()
            
        # Clear context data from Redis
        from agents.agent.memory.agent_context_manager import agent_context_manager
        agent_context_manager.clear_all(conversation_id)

    async def add_memory(self, conversation_id: str, current_time: datetime):
        """
        Add memory to the agent based on the conversation ID.
        """
        memory_list = self.redis_memory.get_memory_by_conversation_id(conversation_id)

        # Add system time to short-term memory
        formatted_time = current_time.strftime('%Y-%m-%d %H:%M:%S %Z')
        timestamp = int(current_time.timestamp())

        self.agent_executor.short_memory.add(
            role="System Time",
            content=f"UTC Now: {formatted_time}, Timestamp: {timestamp}"
        )
        # self.agent_executor.short_memory.add(
        #     role="User Info",
        #     content=f"Wallet address of the user: {self.chat_context.user.get('wallet_address', '')}"
        # )

        # Load conversation-specific memory into the agent
        self.agent_executor.add_memory_object(memory_list)
