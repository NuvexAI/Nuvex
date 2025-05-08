import json
import logging
from typing import Optional, AsyncIterator, Any, Dict

import httpx
from pydantic import BaseModel

from agents.agent.entity.inner.tool_output import ToolOutput
from agents.agent.executor.executor import AgentExecutor
from agents.agent.memory.memory import MemoryObject
from agents.common.config import SETTINGS
from agents.models.entity import ChatContext

logger = logging.getLogger(__name__)

class DeepThinkDto(BaseModel):
    """
    Data transfer object for deep analysis request
    """
    q: str  # Query string for deep analysis

class DeepThinkingExecutor(AgentExecutor):
    """
    Advanced agent executor with sophisticated cognitive processing capabilities.
    This executor connects to specialized thinking services to process and respond to complex queries with deep insights.
    """

    def __init__(self,
                 chat_context: ChatContext,
                 name: str,
                 llm: Optional[Any] = None,
                 role_settings: str = "",
                 **kwargs) -> None:
        """
        Initialize a DeepThinkingExecutor.
        
        Args:
            chat_context: Chat context containing conversation information
            name: Name of the agent
            llm: Language model instance (not used in this executor)
            role_settings: Role configuration (not used in this executor)
            **kwargs: Additional arguments passed to parent class
        """
        super().__init__(
            chat_context=chat_context,
            name=name,
            llm=llm,
            role_settings=role_settings,
            **kwargs
        )
        self.conversation_history = []
        # Configure base URL and API key
        self.api_base = SETTINGS.DATA_API_BASE  # Get API base URL from configuration
        self.api_key = SETTINGS.DATA_API_KEY  # Get API key from configuration
        self._current_event = None  # To track the current event type

    async def stream(
            self,
            task: Optional[str] = None,
            img: Optional[str] = None,
            *args,
            **kwargs,
    ) -> AsyncIterator[ToolOutput]:
        """
        Stream responses from the advanced cognitive processing engine.
        
        Args:
            task: The user's query or task
            img: Optional image data (not used in this executor)
            *args: Additional positional arguments
            **kwargs: Additional keyword arguments
            
        Yields:
            Text chunks from the deep thinking response
        """
        if not task:
            yield "Please provide a question or task."
            return
        
        # Call the specialized cognitive service and stream the response
        try:
            
            async for data in self._call_deep_api(task):
                yield ToolOutput(data)
                
        except Exception as e:
            error_message = f"Error in cognitive processing: {str(e)}"
            logger.error(error_message, exc_info=True)
            yield error_message

    def _process_sse_data(self, data: Dict[str, str]) -> str:
        """
        Process SSE event data and extract relevant text.
        
        Args:
            data: Dictionary containing event and data fields
            
        Returns:
            Extracted text from role_ai_markdown messages, or empty string
        """
        if not data or 'data' not in data:
            return ""
            
        try:
            # Parse the data JSON
            json_data = json.loads(data['data'])
            
            # Only extract text from role_ai_markdown type messages
            if json_data.get("type") == "role_ai_markdown":
                text = json_data.get("text", "")
                
                # Remove "Solution: " prefix if present
                if text.startswith("Solution: "):
                    text = text[10:]
                    
                # Remove "Next request." suffix if present
                if text.endswith(" Next request."):
                    text = text[:-14]
                    
                return text
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error in SSE data: {e}")
        except Exception as e:
            logger.error(f"Error processing SSE data: {e}")
        
        # Return empty string for non-relevant data
        return ""

    def add_memory_object(self, memory_list: list[MemoryObject]):
        """
        Add memory objects to the conversation history.
        
        Args:
            memory_list: List of memory objects to add
        """
        for memory in memory_list:
            self.conversation_history.append({"role": "user", "content": memory.input})
            if memory.output:
                self.conversation_history.append({"role": "assistant", "content": memory.output})

    def _format_conversation_history(self) -> str:
        """
        Format the conversation history into a single string for the cognitive engine.
        
        Returns:
            Formatted conversation history
        """
        formatted_history = ""
        for i, message in enumerate(self.conversation_history):
            if message["role"] == "user":
                formatted_history += f"User: {message['content']}\n"
            else:
                formatted_history += f"Assistant: {message['content']}\n"
        
        # Get the last user message (current query)
        current_query = next((msg["content"] for msg in reversed(self.conversation_history) 
                           if msg["role"] == "user"), "")
        
        # If we have conversation history, append it to the query
        if len(self.conversation_history) > 1:
            return f"{current_query}\n\nConversation history:\n{formatted_history}"
        
        return current_query

    async def _call_deep_api(self, query: str) -> AsyncIterator[str]:
        """
        Connect to the specialized deep thinking service.
        
        Args:
            query: The query to process with advanced cognitive analysis
            
        Yields:
            Parsed SSE events with event type and data
        """
        url = f"{self.api_base}/p/agent/stream/deep-think"
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key
        }
        
        payload = {"q": query}
        
        async with httpx.AsyncClient() as client:
            try:
                async with client.stream(
                    "POST",
                    url, 
                    headers=headers, 
                    json=payload, 
                    timeout=httpx.Timeout(120.0)  # Longer timeout for deep thinking
                ) as response:
                    response.raise_for_status()

                    async for line in response.aiter_lines():
                        yield line + '\n'

                            
            except httpx.RequestError as e:
                logger.error(f"Request error for deep thinking: {str(e)}", exc_info=True)
                raise e