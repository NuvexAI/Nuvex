import json
import logging

import tiktoken

logger = logging.getLogger(__name__)


class TokenLimiter:
    """A utility class for limiting and counting tokens in text"""

    def __init__(self, max_tokens=10000, gpt_encoder="cl100k_base"):
        """
        Initialize TokenLimiter

        Args:
            max_tokens (int): Maximum allowed tokens, defaults to 10000
            gpt_encoder (str): Name of the encoder to use, defaults to "cl100k_base"
        """
        self.max_tokens = max_tokens
        self.gpt_encoder = gpt_encoder

    def limit_tokens(self, data, max_tokens=None):
        """
        Truncate a dictionary or list of dictionaries to fit within a maximum token limit

        Args:
            data (dict or list): Dictionary or list of dictionaries to be truncated
            max_tokens (int): Maximum allowed number of tokens

        Returns:
            dict or list: Truncated data structure
        """
        if not max_tokens:
            max_tokens = self.max_tokens

        json_str = json.dumps(data)
        if self.count_tokens(json_str) <= max_tokens:
            return data

        if isinstance(data, dict):
            truncated_data = {}
            current_tokens = self.count_tokens("{}")  # Initial tokens

            for key, value in data.items():
                value_str = json.dumps(value)
                tokens_to_add = self.count_tokens(f'"{key}":{value_str},')

                if current_tokens + tokens_to_add > max_tokens:
                    break

                truncated_data[key] = value
                current_tokens += tokens_to_add
            return truncated_data

        elif isinstance(data, list):
            truncated_data = []
            current_tokens = self.count_tokens("[]")  # Initial tokens

            for item in data:
                item_str = json.dumps(item)
                tokens_to_add = self.count_tokens(item_str + ",")

                if current_tokens + tokens_to_add > max_tokens:
                    break

                truncated_data.append(item)
                current_tokens += tokens_to_add
            return truncated_data

        return data

    def count_tokens(self, text: str) -> int:
        """
        Calculate the number of tokens in a text string

        Args:
            text (str): Text to count tokens for

        Returns:
            int: Number of tokens in the text
        """
        try:
            encoding = tiktoken.get_encoding(self.gpt_encoder)
            return len(encoding.encode(text))
        except Exception as e:
            logger.error(f"Error counting tokens: {e}")
            return len(text) // 4  # Rough estimate, assuming 4 chars per token
