import json
from typing import Dict, Any

from agents.agent.entity.inner.inner_output import Output
from agents.agent.tools.message_tool import send_message


class CustomOutput(Output):
    """
    Custom output class for handling various types of analysis results
    """
    
    def __init__(self, data: Dict[str, Any], output_type: str = "message"):
        """
        Initialize CustomOutput object
        
        Args:
            data: Dictionary containing analysis results
            output_type: Type of the output, defaults to "custom"
        """
        self.data = data
        self.output_type = output_type

    def to_stream(self) -> str:
        return send_message(self.output_type, self.data)

    def get_response(self) -> str:
        return json.dumps(self.to_stream(), ensure_ascii=False)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert CustomOutput object to dictionary
        
        Returns:
            Dict: Dictionary containing type and data fields
        """
        return {
            "type": self.output_type,
            "data": self.data
        } 