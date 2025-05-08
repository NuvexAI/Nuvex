import logging
from typing import Optional, Tuple, Union

from agents.agent.entity.inner.think_output import ThinkOutput

logger = logging.getLogger(__name__)

class SlidingWindow:
    """
    Sliding window class for processing text streams and tag recognition
    """
    
    def __init__(self, window_size: int = 10):
        """
        Initialize the sliding window
        
        Args:
            window_size: Window size, default is 10
        """
        self.window_size = window_size
        self.buffer = ""
        self.think_buffer = ""
        self.in_think_tag = False
    
    def process_char(self, char: str) -> Optional[Union[str, ThinkOutput]]:
        """
        Process a single character and return the content to be output
        
        Args:
            char: Input character
            
        Returns:
            Content to be output, which may be a string or ThinkOutput object, or None if there is no content to output
        """
        if self.in_think_tag:
            return self._process_in_think_tag(char)
        else:
            return self._process_normal_text(char)
    
    def _process_in_think_tag(self, char: str) -> Optional[Union[str, ThinkOutput]]:
        """
        Process characters within the think tag
        
        Args:
            char: Input character
            
        Returns:
            Content to be output, which may be a ThinkOutput object, or None if there is no content to output
        """
        # Accumulate thinking content within the tag
        self.think_buffer += char
        
        # Check if the think tag ends
        if "</think>" in self.think_buffer:
            # Find the position of the </think> tag
            end_tag_pos = self.think_buffer.find("</think>")
            # Extract the thinking content (excluding the </think> tag)
            final_think_content = self.think_buffer[:end_tag_pos]
            
            # Process content after the </think> tag
            remaining = self.think_buffer[end_tag_pos + 8:]
            self.think_buffer = ""
            self.in_think_tag = False
            
            # If there is content after </think>, add it to the normal buffer
            if remaining:
                self.buffer = remaining
            
            # If there is thinking content, return a ThinkOutput object
            if final_think_content:
                return ThinkOutput().write_text(final_think_content)
            return None
        
        # True sliding window behavior for think content
        # When buffer reaches window size, output the first character and slide the window
        if len(self.think_buffer) > self.window_size:
            output_char = self.think_buffer[0]
            self.think_buffer = self.think_buffer[1:]
            return ThinkOutput().write_text(output_char)
        
        return None
    
    def _process_normal_text(self, char: str) -> Optional[Union[str, ThinkOutput]]:
        """
        Process normal text characters
        
        Args:
            char: Input character
            
        Returns:
            Content to be output, which may be a string, or None if there is no content to output
        """
        # Accumulate normal content
        self.buffer += char
        
        # Check if a think tag starts
        if "<think>" in self.buffer:
            # Find the position of the <think> tag
            start_tag_pos = self.buffer.find("<think>")
            # Extract content before the <think> tag
            pre_content = self.buffer[:start_tag_pos]
            
            # Process content after the <think> tag
            self.buffer = self.buffer[start_tag_pos + 7:]
            self.in_think_tag = True
            
            # If there is content, return it
            if pre_content:
                return pre_content
            return None
        
        # True sliding window behavior for normal content
        # When buffer reaches window size, output the first character and slide the window
        if len(self.buffer) > self.window_size:
            output_char = self.buffer[0]
            self.buffer = self.buffer[1:]
            return output_char
        
        return None
    
    def get_remaining(self) -> Tuple[Optional[str], Optional[ThinkOutput]]:
        """
        Get the remaining buffer content
        
        Returns:
            A tuple of (normal content, thinking content), None if there is no corresponding content
        """
        normal_output = self.buffer if self.buffer else None
        think_output = ThinkOutput().write_text(self.think_buffer) if self.think_buffer else None
        
        # Clear buffers
        self.buffer = ""
        self.think_buffer = ""
        
        return normal_output, think_output 