import logging
from typing import Optional

from cryptography.fernet import Fernet

from agents.common.config import SETTINGS

logger = logging.getLogger(__name__)

class EncryptionUtils:
    def __init__(self, encryption_key: str):
        """
        Initialize encryption utility class
        
        :param encryption_key: Encryption key
        """
        self.cipher_suite = Fernet(encryption_key.encode())
    
    def encrypt(self, data: str) -> Optional[str]:
        """
        Encrypt string data
        
        :param data: String to encrypt
        :return: Encrypted string, or None if input is empty
        """
        if not data:
            return None
        try:
            return self.cipher_suite.encrypt(data.encode()).decode()
        except Exception as e:
            logger.error(f"Error encrypting data: {e}", exc_info=True)
            return None
    
    def decrypt(self, encrypted_data: str) -> Optional[str]:
        """
        Decrypt string data
        
        :param encrypted_data: Encrypted string
        :return: Decrypted original string, or None if input is empty
        """
        if not encrypted_data:
            return None
        try:
            return self.cipher_suite.decrypt(encrypted_data.encode()).decode()
        except Exception as e:
            logger.error(f"Error decrypting data: {e}", exc_info=True)
            return None
    
    def mask_token(self, token: str) -> Optional[str]:
        """
        Mask token by hiding the middle part
        
        :param token: Original token
        :return: Masked token, or None if input is empty
        """
        if not token:
            return None
        
        parts = token.split(':')
        if len(parts) != 2:
            # If token is not in standard format, show only first and last 1/4 of characters
            length = len(token)
            visible_chars = max(2, length // 8)
            return token[:visible_chars] + '*' * (length - 2 * visible_chars) + token[-visible_chars:]
        
        bot_id = parts[0]
        api_part = parts[1]
        
        # If api_part length is less than 8, show only first 2 and last 2 characters
        if len(api_part) <= 8:
            masked_api = api_part[:2] + '*' * (len(api_part) - 4) + api_part[-2:]
        else:
            # Otherwise show first 4 and last 4 characters
            masked_api = api_part[:4] + '*' * (len(api_part) - 8) + api_part[-4:]
        
        return f"{bot_id}:{masked_api}"


# Create global encryption utility instance
encryption_utils = EncryptionUtils(SETTINGS.ENCRYPTION_KEY) 