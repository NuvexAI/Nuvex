import json
import logging
from datetime import datetime
from typing import Any, Optional, List, Dict

import redis

from agents.common.config import SETTINGS
from agents.common.json_encoder import universal_decoder, UniversalEncoder

logger = logging.getLogger(__name__)

def datetime_serializer(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError("Type not serializable")

class RedisUtils:
    def __init__(self, host: str = 'localhost', port: int = 6379, db: int = 0, password: Optional[str] = None,
                 ssl=False):
        """
        Initialize the Redis connection.

        :param host: Redis server host.
        :param port: Redis server port.
        :param db: Redis database index.
        :param password: Redis password (if required).
        """
        self.client = redis.StrictRedis(
            host=host,
            port=port,
            db=db,
            password=password,
            decode_responses=True,
            ssl=ssl
        )

    def set_value(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        """
        Set a value in Redis.

        :param key: Key name.
        :param value: Value to set.
        :param ex: Expiration time in seconds (optional).
        :return: True if successful, False otherwise.
        """
        try:
            return self.client.set(key, value, ex=ex)
        except redis.RedisError as e:
            print(f"Error setting value: {e}")
            return False

    def get_value(self, key: str) -> Optional[Any]:
        """
        Get a value from Redis.

        :param key: Key name.
        :return: Value if the key exists, None otherwise.
        """
        try:
            return self.client.get(key)
        except redis.RedisError as e:
            logger.error(f"Error getting value: {e}", exc_info=True)
            return None

    def delete_key(self, key: str) -> int:
        """
        Delete a key from Redis.

        :param key: Key name.
        :return: Number of keys removed.
        """
        try:
            return self.client.delete(key)
        except redis.RedisError as e:
            logger.error(f"Error deleting key: {e}", exc_info=True)
            return 0

    def push_to_list(self, key: str, value: Any, max_length: Optional[int] = None, ttl: int = None) -> None:
        """
        Push a serialized value to a list in Redis.

        :param key: Key name.
        :param value: Value to push (can be a structure).
        :param max_length: Maximum length of the list (optional).
        :param ttl: Time to live in seconds (default 5 days).
        """
        try:
            serialized_value = json.dumps(value, cls=UniversalEncoder)  # Serialize to JSON
            pipe = self.client.pipeline()
            pipe.rpush(key, serialized_value)
            if ttl:
                pipe.expire(key, ttl)
            if max_length is not None:
                pipe.ltrim(key, -max_length, -1)
            pipe.execute()
        except redis.RedisError as e:
            logger.error(f"Error pushing to list: {e}", exc_info=True)

    def get_list(self, key: str, start: int = 0, end: int = -1) -> List[Any]:
        """
        Get a range of deserialized elements from a list in Redis.

        :param key: Key name.
        :param start: Start index (inclusive).
        :param end: End index (inclusive).
        :return: List of deserialized elements.
        """
        try:
            raw_list = self.client.lrange(key, start, end)
            return [json.loads(item, object_hook=universal_decoder) for item in raw_list]  # Deserialize JSON
        except redis.RedisError as e:
            logger.error(f"Error getting list: {e}", exc_info=True)
            return []
        except json.JSONDecodeError as e:
            logger.error(f"Error deserializing list: {e}", exc_info=True)
            return []

    def set_hash(self, key: str, mapping: Dict[str, Any]) -> bool:
        """
        Set multiple fields in a Redis hash.

        :param key: Key name.
        :param mapping: Dictionary of field-value pairs.
        :return: True if successful, False otherwise.
        """
        try:
            return self.client.hmset(key, mapping)
        except redis.RedisError as e:
            logger.error(f"Error setting hash: {e}", exc_info=True)
            return False

    def get_hash(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Get all fields and values from a Redis hash.

        :param key: Key name.
        :return: Dictionary of field-value pairs, or None if the hash does not exist.
        """
        try:
            return self.client.hgetall(key)
        except redis.RedisError as e:
            logger.error(f"Error getting hash: {e}", exc_info=True)
            return None

    def add_to_set(self, key: str, *values: Any) -> int:
        """
        Add one or more members to a set.

        :param key: Key name.
        :param values: Values to add.
        :return: Number of elements added to the set.
        """
        try:
            return self.client.sadd(key, *values)
        except redis.RedisError as e:
            logger.error(f"Error adding to set: {e}", exc_info=True)
            return 0

    def get_set_members(self, key: str) -> Optional[set]:
        """
        Get all members of a set.

        :param key: Key name.
        :return: Set of members, or None if the key does not exist.
        """
        try:
            return self.client.smembers(key)
        except redis.RedisError as e:
            logger.error(f"Error getting set members: {e}", exc_info=True)
            return None

    def get_keys_by_pattern(self, pattern: str) -> List[str]:
        """
        Get all keys matching a pattern.

        :param pattern: Pattern to match (e.g., "prefix:*").
        :return: List of matching keys.
        """
        try:
            return self.client.keys(pattern)
        except redis.RedisError as e:
            logger.error(f"Error getting keys by pattern: {e}", exc_info=True)
            return []

    def delete_keys(self, keys: List[str]) -> int:
        """
        Delete multiple keys from Redis.

        :param keys: List of keys to delete.
        :return: Number of keys removed.
        """
        if not keys:
            return 0
            
        try:
            return self.client.delete(*keys)
        except redis.RedisError as e:
            logger.error(f"Error deleting multiple keys: {e}", exc_info=True)
            return 0

    def set_expiry(self, key: str, seconds: int) -> bool:
        """
        Set expiration time for a key.

        :param key: Key name.
        :param seconds: Expiration time in seconds.
        :return: True if successful, False otherwise.
        """
        try:
            return self.client.expire(key, seconds)
        except redis.RedisError as e:
            logger.error(f"Error setting expiry: {e}", exc_info=True)
            return False

    def remove_from_set(self, key: str, *values: Any) -> int:
        """
        Remove one or more members from a set.

        :param key: Key name.
        :param values: Values to remove.
        :return: Number of elements removed from the set.
        """
        try:
            return self.client.srem(key, *values)
        except redis.RedisError as e:
            logger.error(f"Error removing from set: {e}", exc_info=True)
            return 0


redis_utils = RedisUtils(
    host=SETTINGS.REDIS_HOST,
    port=SETTINGS.REDIS_PORT,
    db=SETTINGS.REDIS_DB,
    password=SETTINGS.REDIS_PASSWORD,
    ssl=SETTINGS.REDIS_SSL
)
