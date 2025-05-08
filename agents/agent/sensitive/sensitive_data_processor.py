import json
import logging
import re
from typing import Any, Dict, List, Tuple

from agents.common.redis_utils import redis_utils

logger = logging.getLogger(__name__)

class SensitiveDataProcessor:
    """
    Processor for handling sensitive data in tool responses and parameters.
    
    This class provides functionality to mask sensitive data in API responses
    and recover original data when needed for subsequent API calls.
    """
    
    def __init__(self, conversation_id: str, redis_expiry_days: int = 7):
        """
        Initialize the sensitive data processor.
        
        Args:
            conversation_id: The unique identifier for the conversation
            redis_expiry_days: Number of days before Redis mappings expire (default: 7)
        """
        self.conversation_id = conversation_id
        self.redis_key = f"sensitive_data:{conversation_id}"
        self.redis_expiry_seconds = redis_expiry_days * 24 * 60 * 60  # Convert days to seconds
        self.reverse_lookup_key = f"sensitive_data_reverse:{conversation_id}"
    
    def process_tool_response(self, tool_name: str, response: Any, config: Dict) -> Any:
        """
        Process the tool response to mask sensitive data according to configuration.
        
        Args:
            tool_name: Name of the tool
            response: The response data from the tool
            config: Configuration for sensitive data handling
            
        Returns:
            Processed response with sensitive data masked
        """
        if not config or not response:
            return response
            
        # Get response sensitive fields configuration
        sensitive_fields = config.get("response", {}).get("sensitive_fields", [])
        if not sensitive_fields:
            return response
            
        # Create a deep copy of the response to avoid modifying the original
        processed_response = json.loads(json.dumps(response))
        
        # Process each sensitive field
        for field_config in sensitive_fields:
            path = field_config.get("path")
            if not path:
                continue
                
            # Get the value at the specified path
            value = self._get_value_by_path(processed_response, path)
            if value is None:
                continue
                
            # Mask the value according to the configuration
            masked_value, identifier = self._mask_value(value, field_config)
            
            # Store the mapping between masked value and original value
            self._store_sensitive_data_mapping(identifier, value, masked_value)
            
            # Set the masked value in the response
            self._set_value_by_path(processed_response, path, masked_value)
        
        return processed_response
    
    def process_tool_parameters(self, tool_name: str, parameters: Dict, config: Dict) -> Dict:
        """
        Process tool parameters to recover sensitive data if needed.
        
        Args:
            tool_name: Name of the tool
            parameters: Parameters to be passed to the tool
            config: Configuration for sensitive data handling
            
        Returns:
            Processed parameters with sensitive data recovered if needed
        """
        if not config:
            return parameters
            
        # Create a deep copy of the parameters to avoid modifying the original
        processed_params = json.loads(json.dumps(parameters))
        
        # Get parameters configuration
        params_config = config.get("parameters", {})
        
        # Process flat key-value parameters (like query, header)
        recoverable_fields = params_config.get("recoverable_fields", [])
        if recoverable_fields:
            for param_type in ["query", "header", "path", "params"]:
                if param_type in processed_params:
                    processed_params[param_type] = self._recover_parameters(
                        processed_params[param_type], 
                        recoverable_fields
                    )
        
        # Process nested parameters (like body)
        nested_fields = params_config.get("nested_fields", [])
        if nested_fields and "body" in processed_params:
            for field_config in nested_fields:
                path = field_config.get("path")
                if not path:
                    continue
                    
                # Get the value at the specified path
                value = self._get_value_by_path(processed_params["body"], path)
                if value is None:
                    continue
                    
                # Recover the original value
                original_value = self._get_original_value(value if isinstance(value, str) else json.dumps(value))
                if original_value:
                    # Set the recovered value in the parameters
                    self._set_value_by_path(processed_params["body"], path, original_value)
        
        return processed_params
    
    def _recover_parameters(self, params: Any, recoverable_fields: List[str]) -> Any:
        """
        Recursively recover sensitive data in parameters.
        
        Args:
            params: Parameters to process
            recoverable_fields: List of field names that should be recovered
            
        Returns:
            Processed parameters with sensitive data recovered
        """
        if isinstance(params, dict):
            result = {}
            for key, value in params.items():
                # Check if this field should be recovered based on field name or parameter flag
                should_recover = key in recoverable_fields
                
                # If the field has a special flag indicating it's sensitive, recover it regardless of name
                if isinstance(value, dict) and value.get("__sensitive", False):
                    should_recover = True
                    
                    # Check if there's a binding key for more precise recovery
                    binding_key = value.get("__binding_key", "")
                    actual_value = value.get("value", "")
                    
                    if binding_key:
                        # Use the binding key to create the identifier and look up the original value
                        identifier = f"__SENSITIVE_DATA_{self.conversation_id}_{binding_key}__"
                        mapping = redis_utils.get_hash(self.redis_key)
                        if mapping and identifier in mapping:
                            try:
                                result[key] = json.loads(mapping[identifier])
                                continue
                            except json.JSONDecodeError:
                                result[key] = mapping[identifier]
                                continue
                    
                    # If no binding key or lookup failed, fall back to the value
                    value = actual_value
                
                if should_recover and isinstance(value, str):
                    # Try to recover the original value
                    original_value = self._get_original_value(value)
                    result[key] = original_value if original_value else value
                else:
                    result[key] = self._recover_parameters(value, recoverable_fields)
            return result
        elif isinstance(params, list):
            return [self._recover_parameters(item, recoverable_fields) for item in params]
        else:
            return params
    
    def _mask_value(self, value: Any, field_config: Dict) -> Tuple[Any, str]:
        """
        Mask a value according to the field configuration.
        
        Args:
            value: The value to mask
            field_config: Configuration for the field
            
        Returns:
            Tuple of (masked_value, identifier)
        """
        if not isinstance(value, str):
            return value, ""
            
        # Check if a custom identifier is provided in the configuration
        custom_identifier = field_config.get("identifier", "")
        
        # If custom identifier is provided, use it; otherwise generate one
        if custom_identifier:
            identifier = f"__SENSITIVE_DATA_{self.conversation_id}_{custom_identifier}__"
        else:
            # Generate a unique identifier for this sensitive data
            identifier = f"__SENSITIVE_DATA_{self.conversation_id}_{hash(value)}__"
        
        # Check if we should add a flag to indicate this is sensitive data
        add_flag = field_config.get("add_flag", False)
        
        mask_type = field_config.get("mask_type", "partial")
        
        if mask_type == "full":
            # Completely mask the value with a reasonable length
            max_mask_length = field_config.get("max_mask_length", 8)
            masked_value = "*" * min(max_mask_length, len(value))
        elif mask_type == "partial":
            # Partially mask the value
            mask_percentage = field_config.get("mask_percentage", 0.6)
            max_mask_length = field_config.get("max_mask_length", 10)
            masked_value = self._partial_mask(value, mask_percentage, max_mask_length)
        elif mask_type == "pattern":
            # Use a specific pattern for masking
            pattern = field_config.get("pattern", "{value}")
            masked_value = self._pattern_mask(value, pattern)
        else:
            masked_value = value
        
        # If flagging is enabled, wrap the masked value in a dictionary with a flag
        if add_flag:
            # If a binding_key is provided, include it in the flagged object
            if custom_identifier:
                return {"__sensitive": True, "value": masked_value, "__binding_key": custom_identifier}, identifier
            else:
                return {"__sensitive": True, "value": masked_value}, identifier
        else:
            return masked_value, identifier
    
    def _partial_mask(self, value: str, mask_percentage: float, max_mask_length: int = 10) -> str:
        """
        Partially mask a string value with a reasonable length.
        
        Args:
            value: The string to mask
            mask_percentage: Percentage of the string to mask (0.0 to 1.0)
            max_mask_length: Maximum length of the mask characters
            
        Returns:
            Partially masked string
        """
        if len(value) <= 3:
            return value
            
        # Calculate how many characters to mask
        mask_length = int(len(value) * mask_percentage)
        
        # Limit the mask length to a reasonable value
        mask_length = min(mask_length, max_mask_length)
        
        # Calculate how many characters to preserve at each end
        preserve_each_end = (len(value) - mask_length) // 2
        preserve_each_end = max(1, preserve_each_end)
        
        # If the value is very long, we'll show fewer characters at each end
        if len(value) > 30:
            preserve_each_end = min(preserve_each_end, 3)
        
        masked_value = value[:preserve_each_end] + '*' * mask_length + value[-preserve_each_end:]
        return masked_value
    
    def _pattern_mask(self, value: str, pattern: str) -> str:
        """
        Mask a value using a specific pattern.
        
        Args:
            value: The value to mask
            pattern: The pattern to use for masking
            
        Returns:
            Masked value according to the pattern
        """
        if "{value}" in pattern:
            return pattern.replace("{value}", value)
        elif "{username}" in pattern and "@" in value:
            username, domain = value.split("@", 1)
            return pattern.replace("{username}", username)
        elif "{last4}" in pattern and len(value) >= 4:
            return pattern.replace("{last4}", value[-4:])
        else:
            return pattern
    
    def _get_value_by_path(self, data: Any, path: str) -> Any:
        """
        Get a value from a nested structure using a dot-notation path.
        
        Args:
            data: The data structure to navigate
            path: The path to the value, using dot notation (e.g., "data.user.email")
            
        Returns:
            The value at the specified path, or None if not found
        """
        if not path:
            return None
            
        # Handle simple dot notation
        if '*' not in path and '[' not in path:
            parts = path.split('.')
            current = data
            for part in parts:
                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    return None
            return current
            
        # Handle array indices
        elif '[' in path and ']' in path:
            # This is a simplified implementation
            # A more robust implementation would handle nested arrays and wildcards
            parts = re.split(r'\.|\[|\]', path)
            parts = [p for p in parts if p]
            
            current = data
            for part in parts:
                if part.isdigit():
                    # Handle array index
                    idx = int(part)
                    if isinstance(current, list) and 0 <= idx < len(current):
                        current = current[idx]
                    else:
                        return None
                else:
                    # Handle object property
                    if isinstance(current, dict) and part in current:
                        current = current[part]
                    else:
                        return None
            return current
            
        return None
    
    def _set_value_by_path(self, data: Any, path: str, value: Any) -> None:
        """
        Set a value in a nested structure using a dot-notation path.
        
        Args:
            data: The data structure to modify
            path: The path to the value, using dot notation
            value: The value to set
        """
        if not path:
            return
            
        # Handle simple dot notation
        if '*' not in path and '[' not in path:
            parts = path.split('.')
            current = data
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            current[parts[-1]] = value
            
        # Handle array indices
        elif '[' in path and ']' in path:
            # This is a simplified implementation
            # A more robust implementation would handle nested arrays and wildcards
            parts = re.split(r'\.|\[|\]', path)
            parts = [p for p in parts if p]
            
            current = data
            for i, part in enumerate(parts[:-1]):
                if part.isdigit():
                    # Handle array index
                    idx = int(part)
                    next_part = parts[i+1] if i+1 < len(parts) else None
                    
                    if not isinstance(current, list):
                        return
                        
                    while len(current) <= idx:
                        current.append({} if next_part and not next_part.isdigit() else [])
                    
                    current = current[idx]
                else:
                    # Handle object property
                    next_part = parts[i+1] if i+1 < len(parts) else None
                    
                    if part not in current:
                        current[part] = {} if next_part and not next_part.isdigit() else []
                    
                    current = current[part]
            
            last_part = parts[-1]
            if last_part.isdigit():
                idx = int(last_part)
                if isinstance(current, list):
                    while len(current) <= idx:
                        current.append(None)
                    current[idx] = value
            else:
                if isinstance(current, dict):
                    current[last_part] = value
    
    def _store_sensitive_data_mapping(self, identifier: str, original_value: Any, masked_value: Any) -> None:
        """
        Store the mapping between an identifier and the original sensitive data.
        Also store a reverse mapping from masked value to original value.
        
        Args:
            identifier: The identifier for the sensitive data
            original_value: The original sensitive data
            masked_value: The masked version of the data
        """
        if not identifier:
            return
            
        # Store in Redis with the conversation ID as part of the key
        mapping = {identifier: json.dumps(original_value)}
        redis_utils.set_hash(self.redis_key, mapping)
        
        # Store reverse mapping from masked value to original value
        # This allows recovery even when only the masked value is available
        if isinstance(masked_value, str):
            reverse_mapping = {masked_value: json.dumps(original_value)}
            redis_utils.set_hash(self.reverse_lookup_key, reverse_mapping)
        
        # Set expiration time (7 days by default)
        redis_utils.client.expire(self.redis_key, self.redis_expiry_seconds)
        redis_utils.client.expire(self.reverse_lookup_key, self.redis_expiry_seconds)
    
    def _get_original_value(self, value: str) -> Any:
        """
        Get the original value for a potentially masked value.
        
        Args:
            value: The potentially masked value
            
        Returns:
            The original value if found, otherwise None
        """
        # Check if this is a direct identifier
        if isinstance(value, str) and value.startswith("__SENSITIVE_DATA_") and value.endswith("__"):
            # Get the mapping from Redis
            mapping = redis_utils.get_hash(self.redis_key)
            if mapping and value in mapping:
                try:
                    return json.loads(mapping[value])
                except json.JSONDecodeError:
                    return mapping[value]
        
        # Try reverse lookup - check if this masked value has a mapping
        if isinstance(value, str):
            reverse_mapping = redis_utils.get_hash(self.reverse_lookup_key)
            if reverse_mapping and value in reverse_mapping:
                try:
                    return json.loads(reverse_mapping[value])
                except json.JSONDecodeError:
                    return reverse_mapping[value]
        
        # If not found in direct mappings, try pattern matching
        if isinstance(value, str):
            # Get all stored sensitive data mappings
            mapping = redis_utils.get_hash(self.redis_key)
            if not mapping:
                return None
                
            # Check if it's a full mask pattern (like ********)
            if re.match(r'^\*+$', value):
                # Find all values using full masking
                for identifier, original_json in mapping.items():
                    try:
                        original = json.loads(original_json)
                        # If the original value's length is similar to the mask length, or the mask is standard length (like 8 *)
                        # This is a heuristic approach and may need adjustment based on actual usage
                        if len(value) == 8 or (isinstance(original, str) and abs(len(original) - len(value)) < 5):
                            return original
                    except (json.JSONDecodeError, TypeError):
                        continue
            
            # Check if it's a partial mask pattern (like abc***xyz)
            elif '*' in value:
                for identifier, original_json in mapping.items():
                    try:
                        original = json.loads(original_json)
                        if not isinstance(original, str):
                            continue
                            
                        # Check if prefix and suffix match
                        prefix = value.split('*')[0]
                        suffix = value.split('*')[-1]
                        
                        if original.startswith(prefix) and original.endswith(suffix):
                            return original
                    except (json.JSONDecodeError, TypeError):
                        continue
            
            # Check if it's a pattern mask (like ****-1234)
            elif re.search(r'\*+-\d{4}$', value):
                # Extract the last 4 digits
                last4 = value[-4:]
                for identifier, original_json in mapping.items():
                    try:
                        original = json.loads(original_json)
                        if isinstance(original, str) and original.endswith(last4):
                            return original
                    except (json.JSONDecodeError, TypeError):
                        continue
        
        return None
    
    def clear_sensitive_data(self) -> None:
        """
        Clear all sensitive data mappings for this conversation.
        """
        redis_utils.delete_key(self.redis_key)
        redis_utils.delete_key(self.reverse_lookup_key)