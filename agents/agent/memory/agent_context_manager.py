import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Set

from agents.common.redis_utils import redis_utils
from agents.models.entity import AgentContextData

logger = logging.getLogger(__name__)

class AgentContextManager:
    """
    Agent context manager for storing and retrieving context data in Redis.
    Provides a structured way to manage context data during agent conversations.
    """
    
    # Common scenario examples (for documentation purposes only)
    # These are just examples and not restrictions - any scenario name can be used
    SCENARIO_USER_CONTEXT = "user_context"
    SCENARIO_SESSION_DATA = "session_data"
    SCENARIO_TOOL_CONTEXT = "tool_context"
    SCENARIO_AGENT_CONTEXT = "agent_context"
    
    # Redis key prefix
    KEY_PREFIX = "agent_context"
    
    # Redis set key suffix for storing scenario names
    SCENARIOS_SET_SUFFIX = "scenarios"
    
    # Default TTL (24 hours)
    DEFAULT_TTL = 86400
    
    @classmethod
    def _build_key(cls, conversation_id: str, scenario: str) -> str:
        """Build Redis key for a specific scenario"""
        return f"{cls.KEY_PREFIX}:{conversation_id}:{scenario}"
    
    @classmethod
    def _build_scenarios_set_key(cls, conversation_id: str) -> str:
        """Build Redis key for the set of scenarios"""
        return f"{cls.KEY_PREFIX}:{conversation_id}:{cls.SCENARIOS_SET_SUFFIX}"
    
    @classmethod
    def _get_scenarios(cls, conversation_id: str) -> Set[str]:
        """Get all scenarios for a conversation from the scenarios set"""
        try:
            scenarios_key = cls._build_scenarios_set_key(conversation_id)
            scenarios = redis_utils.get_set_members(scenarios_key)
            return scenarios or set()
        except Exception as e:
            logger.error(f"Error getting scenarios for conversation {conversation_id}: {str(e)}", exc_info=True)
            return set()
    
    @classmethod
    def store(cls, conversation_id: str, scenario: str, data: Dict, ttl: int = DEFAULT_TTL, **metadata) -> bool:
        """
        Store context data in Redis
        
        Args:
            conversation_id: Conversation ID
            scenario: Scenario identifier for the context data (can be any string)
            data: Context data to store
            ttl: Time to live in seconds
            metadata: Additional metadata
            
        Returns:
            bool: Whether the operation was successful
        """
        try:
            # Add default metadata
            metadata.update({
                "created_at": datetime.now().isoformat(),
                "ttl": ttl
            })
            
            # Create AgentContextData instance
            context_data = AgentContextData.create(scenario, data, **metadata)
            
            # Store in Redis
            key = cls._build_key(conversation_id, scenario)
            json_data = json.dumps(context_data.to_dict(), ensure_ascii=False)
            result = redis_utils.set_value(key, json_data, ex=ttl)
            
            # Add scenario to the scenarios set
            scenarios_key = cls._build_scenarios_set_key(conversation_id)
            redis_utils.add_to_set(scenarios_key, scenario)
            # Set expiration for the scenarios set
            redis_utils.set_expiry(scenarios_key, ttl)
            
            logger.info(f"Stored context data for conversation {conversation_id}, scenario {scenario}")
            return result
        except Exception as e:
            logger.error(f"Error storing context data: {str(e)}", exc_info=True)
            return False
    
    @classmethod
    def get(cls, conversation_id: str, scenario: Optional[str] = None) -> Dict[str, Any]:
        """
        Retrieve context data from Redis
        
        Args:
            conversation_id: Conversation ID
            scenario: Optional scenario identifier. If provided, only data for this scenario is returned.
                      If None, data for all scenarios is returned.
            
        Returns:
            Dict[str, Any]: Dictionary mapping scenario names to their data.
                           If scenario is specified, returns {scenario: data} or {} if not found.
        """
        if scenario:
            # Get data for a specific scenario
            try:
                key = cls._build_key(conversation_id, scenario)
                data = redis_utils.get_value(key)
                
                if data:
                    # Parse as AgentContextData instance
                    context_data = AgentContextData.from_dict(json.loads(data))
                    # Return only the data part
                    return {scenario: context_data.data}
                return {}
            except Exception as e:
                logger.error(f"Error retrieving context data for scenario {scenario}: {str(e)}", exc_info=True)
                return {}
        else:
            # Get data for all scenarios
            return cls.get_all_scenarios(conversation_id)
    
    @classmethod
    def get_with_metadata(cls, conversation_id: str, scenario: Optional[str] = None) -> Dict[str, AgentContextData]:
        """
        Retrieve context data from Redis, including metadata
        
        Args:
            conversation_id: Conversation ID
            scenario: Optional scenario identifier. If provided, only data for this scenario is returned.
                      If None, data for all scenarios is returned.
            
        Returns:
            Dict[str, AgentContextData]: Dictionary mapping scenario names to their AgentContextData instances.
                                        If scenario is specified, returns {scenario: data} or {} if not found.
        """
        if scenario:
            # Get data for a specific scenario
            try:
                key = cls._build_key(conversation_id, scenario)
                data = redis_utils.get_value(key)
                
                if data:
                    # Parse as AgentContextData instance
                    context_data = AgentContextData.from_dict(json.loads(data))
                    return {scenario: context_data}
                return {}
            except Exception as e:
                logger.error(f"Error retrieving context data with metadata for scenario {scenario}: {str(e)}", exc_info=True)
                return {}
        else:
            # Get data for all scenarios
            return cls.get_all_with_metadata(conversation_id)
    
    @classmethod
    def delete(cls, conversation_id: str, scenario: Optional[str] = None) -> bool:
        """
        Delete context data from Redis
        
        Args:
            conversation_id: Conversation ID
            scenario: Optional scenario identifier. If provided, only data for this scenario is deleted.
                      If None, data for all scenarios is deleted.
            
        Returns:
            bool: Whether the operation was successful
        """
        if scenario:
            # Delete data for a specific scenario
            try:
                key = cls._build_key(conversation_id, scenario)
                result = redis_utils.delete_key(key) > 0
                
                if result:
                    # Remove scenario from the scenarios set
                    scenarios_key = cls._build_scenarios_set_key(conversation_id)
                    redis_utils.remove_from_set(scenarios_key, scenario)
                    logger.info(f"Deleted context data for conversation {conversation_id}, scenario {scenario}")
                
                return result
            except Exception as e:
                logger.error(f"Error deleting context data for scenario {scenario}: {str(e)}", exc_info=True)
                return False
        else:
            # Delete data for all scenarios
            cls.clear_all(conversation_id)
            return True
    
    @classmethod
    def get_all_scenarios(cls, conversation_id: str, scenarios: List[str] = None) -> Dict[str, Any]:
        """
        Retrieve all scenario data for a specific conversation
        
        Args:
            conversation_id: Conversation ID
            scenarios: Optional list of scenarios to retrieve. If None, all available scenarios are retrieved.
            
        Returns:
            Dict[str, Any]: Mapping of scenario names to data
        """
        result = {}
        
        try:
            if scenarios:
                # Get data for specific scenarios
                for scenario in scenarios:
                    data_dict = cls.get(conversation_id, scenario)
                    if data_dict:
                        result.update(data_dict)
            else:
                # Get all scenarios from the scenarios set
                all_scenarios = cls._get_scenarios(conversation_id)
                
                # Get data for each scenario
                for scenario in all_scenarios:
                    key = cls._build_key(conversation_id, scenario)
                    data = redis_utils.get_value(key)
                    if data:
                        context_data = AgentContextData.from_dict(json.loads(data))
                        result[scenario] = context_data.data
        except Exception as e:
            logger.error(f"Error retrieving all scenario data: {str(e)}", exc_info=True)
        
        return result
    
    @classmethod
    def get_all_with_metadata(cls, conversation_id: str, scenarios: List[str] = None) -> Dict[str, AgentContextData]:
        """
        Retrieve all scenario data for a specific conversation, including metadata
        
        Args:
            conversation_id: Conversation ID
            scenarios: Optional list of scenarios to retrieve. If None, all available scenarios are retrieved.
            
        Returns:
            Dict[str, AgentContextData]: Mapping of scenario names to AgentContextData instances
        """
        result = {}
        
        try:
            if scenarios:
                # Get data for specific scenarios
                for scenario in scenarios:
                    data_dict = cls.get_with_metadata(conversation_id, scenario)
                    if data_dict:
                        result.update(data_dict)
            else:
                # Get all scenarios from the scenarios set
                all_scenarios = cls._get_scenarios(conversation_id)
                
                # Get data for each scenario
                for scenario in all_scenarios:
                    key = cls._build_key(conversation_id, scenario)
                    data = redis_utils.get_value(key)
                    if data:
                        context_data = AgentContextData.from_dict(json.loads(data))
                        result[scenario] = context_data
        except Exception as e:
            logger.error(f"Error retrieving all scenario data with metadata: {str(e)}", exc_info=True)
        
        return result
    
    @classmethod
    def clear_all(cls, conversation_id: str, scenarios: List[str] = None) -> None:
        """
        Clear all context data for a specific conversation
        
        Args:
            conversation_id: Conversation ID
            scenarios: Optional list of scenarios to clear. If None, all available scenarios are cleared.
        """
        try:
            if scenarios:
                # Clear data for specific scenarios
                for scenario in scenarios:
                    cls.delete(conversation_id, scenario)
            else:
                # Get all scenarios from the scenarios set
                all_scenarios = cls._get_scenarios(conversation_id)
                
                # Delete data for each scenario
                for scenario in all_scenarios:
                    key = cls._build_key(conversation_id, scenario)
                    redis_utils.delete_key(key)
                
                # Delete the scenarios set
                scenarios_key = cls._build_scenarios_set_key(conversation_id)
                redis_utils.delete_key(scenarios_key)
                
                logger.info(f"Cleared all context data for conversation {conversation_id}")
        except Exception as e:
            logger.error(f"Error clearing all context data: {str(e)}", exc_info=True)
    
    @classmethod
    def list_scenarios(cls, conversation_id: str) -> List[str]:
        """
        List all available scenarios for a conversation
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            List[str]: List of scenario names
        """
        try:
            scenarios = cls._get_scenarios(conversation_id)
            return list(scenarios)
        except Exception as e:
            logger.error(f"Error listing scenarios: {str(e)}", exc_info=True)
            return []

# Create a singleton instance for easy import and use
agent_context_manager = AgentContextManager() 