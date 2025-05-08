from typing import Any

from agents.agent.entity.agent_mode import AgentMode
from agents.agent.executor.agent_executor import DeepAgentExecutor
from agents.agent.executor.deep_thinking_executor import DeepThinkingExecutor
from agents.agent.executor.prompt_executor import PromptAgentExecutor
from agents.models.entity import ChatContext


class AgentExecutorFactory:
    """Agent executor factory class"""
    
    @staticmethod
    def create_executor(mode: AgentMode, chat_context: ChatContext, **kwargs) -> Any:
        """
        Create an agent executor based on the specified mode.
        
        Args:
            mode: The execution mode (ReAct/Prompt/Function/DeepThinking)
            **kwargs: Keyword arguments including:
                - name: Name of the agent
                - user_name: Name of the user
                - llm: Language model instance
                - system_prompt: System prompt text
                - description: Agent description
                - role_settings: Role configuration
                - api_tool: List of API tools
                - node_massage_enabled: Enable node messages
                - output_type: Type of output
                - output_detail_enabled: Enable detailed output
                - max_loops: Maximum number of loops
                - retry: Number of retries
                - stop_func: Function to check stop condition
                - tokenizer: Tokenizer instance
                - long_term_memory: Long-term memory instance
        
        Returns:
            An instance of AgentExecutor
            
        Raises:
            ValueError: If the mode is invalid or unsupported
        """

        if mode == AgentMode.PROMPT:
            # Prompt mode: Simple conversation without tool calling
            return PromptAgentExecutor(chat_context=chat_context, **kwargs)
            
        elif mode == AgentMode.REACT:
            # ReAct mode: Full agent capabilities
            return DeepAgentExecutor(chat_context=chat_context, **kwargs)
            
        elif mode == AgentMode.FUNCTION:
            # Function mode: Focused on API and function calls
            # TODO: Implement FunctionAgentExecutor
            raise NotImplementedError("Function mode not implemented yet")
            
        elif mode == AgentMode.DEEP_THINKING:
            # DeepThinking mode: Advanced cognitive processing capabilities
            return DeepThinkingExecutor(chat_context=chat_context, **kwargs)
            
        else:
            raise ValueError(f"Unsupported agent mode: {mode}") 