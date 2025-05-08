from enum import Enum

class AgentMode(Enum):
    """Agent execution mode enum"""
    REACT = "ReAct"     # ReAct mode for complex task decomposition and tool calling
    PROMPT = "Prompt"   # Simple prompt mode for direct conversation
    FUNCTION = "Function"  # Function mode focused on API and function calls
    DEEP_THINKING = "DeepThinking"  # Advanced mode with sophisticated cognitive processing capabilities