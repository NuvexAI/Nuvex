import hashlib
import hmac
import logging
import uuid
from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from agents.exceptions import CustomAgentException, ErrorCode
from agents.models.models import OpenPlatformKey

logger = logging.getLogger(__name__)

# Remove JWT and token secret configuration
# TOKEN_SECRET = "open_platform_token_secret"  # In production, this should be stored in environment variables or config files
# Token validity period is now permanent, no expiration

def generate_key_pair():
    """Generate a new access key and secret key pair for open platform"""
    access_key = f"ak_{uuid.uuid4().hex[:16]}"
    secret_key = f"sk_{uuid.uuid4().hex}"
    return access_key, secret_key

def generate_signature(access_key: str, secret_key: str, timestamp: str) -> str:
    """Generate signature for open platform API request"""
    message = f"{access_key}{timestamp}"
    return hmac.new(
        secret_key.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()

def verify_signature(access_key: str, secret_key: str, timestamp: str, signature: str) -> bool:
    """Verify open platform API signature"""
    expected_signature = generate_signature(access_key, secret_key, timestamp)
    return hmac.compare_digest(signature, expected_signature)

async def get_or_create_credentials(user: dict, session: AsyncSession) -> dict:
    """Get existing credentials or create new ones if they don't exist"""
    user_id = user.get("user_id")
    if not user_id:
        raise CustomAgentException(
            error_code=ErrorCode.INVALID_PARAMETERS,
            message="User ID is required"
        )

    # Try to get existing credentials
    query = select(OpenPlatformKey).where(
        OpenPlatformKey.user_id == user_id,
        OpenPlatformKey.is_deleted == False
    )
    result = await session.execute(query)
    credentials = result.scalar_one_or_none()
    
    if credentials:
        return {
            "access_key": credentials.access_key,
            "secret_key": credentials.secret_key,
            "token": credentials.token
        }
    
    # Create new credentials if none exist
    access_key, secret_key = generate_key_pair()
    token = generate_token_string()
    credentials = OpenPlatformKey(
        name=f"User {user_id} Open Platform Key",
        access_key=access_key,
        secret_key=secret_key,
        token=token,
        user_id=user_id,
        created_at=datetime.utcnow()
    )
    
    session.add(credentials)
    await session.commit()
    
    return {
        "access_key": access_key,
        "secret_key": secret_key,
        "token": token,
    }

async def get_credentials(access_key: str, session: AsyncSession) -> Optional[OpenPlatformKey]:
    """Get credentials by access key"""
    query = select(OpenPlatformKey).where(
        OpenPlatformKey.access_key == access_key,
        OpenPlatformKey.is_deleted == False
    )
    result = await session.execute(query)
    return result.scalar_one_or_none()


async def get_credentials_by_token(token: str, session: AsyncSession) -> Optional[OpenPlatformKey]:
    """Get credentials by token"""
    query = select(OpenPlatformKey).where(
        OpenPlatformKey.token == token,
        OpenPlatformKey.is_deleted == False
    )
    result = await session.execute(query)
    return result.scalar_one_or_none()

async def verify_token_and_get_credentials(token: str, session: AsyncSession) -> Optional[Dict[str, Any]]:
    """Verify token and get credentials"""
    if not token or not token.startswith("tk_") or len(token) != 23:  # "tk_" + 20 chars
        return None
        
    from sqlalchemy import select
    from agents.models.models import OpenPlatformKey, User

    stmt = (
        select(OpenPlatformKey, User)
        .join(User, OpenPlatformKey.user_id == User.id)
        .where(OpenPlatformKey.token == token)
    )
    
    result = await session.execute(stmt)
    row = result.first()
    
    if not row:
        return None
        
    credentials, user = row
    
    return {
        "user_id": credentials.user_id,
        "type": "api_token",
        "access_key": credentials.access_key,
        "tenant_id": user.tenant_id
    }

def generate_token_string() -> str:
    """Generate a new token string"""
    # Generate a simple token, using UUID to ensure uniqueness
    # Using 20 characters instead of 16 to further reduce collision probability
    return f"tk_{uuid.uuid4().hex[:20]}"

async def save_token(access_key: str, token: str, session: AsyncSession) -> None:
    """Save token to database"""
    try:
        # Store token in database
        stmt = (
            update(OpenPlatformKey)
            .where(OpenPlatformKey.access_key == access_key)
            .values(token=token, token_created_at=datetime.utcnow())
        )
        await session.execute(stmt)
        await session.commit()
    except Exception as e:
        logger.error(f"Error saving token: {str(e)}", exc_info=True)
        await session.rollback()
        raise

async def generate_token(access_key: str, session: AsyncSession) -> Dict[str, Any]:
    """Generate a token for open platform API access"""
    credentials = await get_credentials(access_key, session)
    if not credentials:
        raise CustomAgentException(
            error_code=ErrorCode.INVALID_PARAMETERS,
            message="Invalid access key"
        )
    
    # Maximum retry attempts for token generation
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            # Generate token string
            token = generate_token_string()
            
            # Save token to database
            await save_token(access_key, token, session)
            
            return {
                "token": token,
            }
        except Exception as e:
            # If there's a unique constraint violation, retry with a new token
            # This assumes the database has a unique constraint on the token field
            if "unique constraint" in str(e).lower() or "duplicate" in str(e).lower():
                retry_count += 1
                if retry_count >= max_retries:
                    logger.error(f"Failed to generate unique token after {max_retries} attempts")
                    raise CustomAgentException(
                        error_code=ErrorCode.INTERNAL_ERROR,
                        message="Failed to generate unique token"
                    )
                # Continue to next iteration to try again
                await session.rollback()
            else:
                # For other errors, raise immediately
                logger.error(f"Error generating token: {str(e)}", exc_info=True)
                await session.rollback()
                raise

def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify basic format of API token"""
    if not token or not token.startswith("tk_") or len(token) != 23:  # "tk_" + 20 chars
        return None
    
    return {"valid": True}

async def reset_token(access_key: str, session: AsyncSession) -> Dict[str, Any]:
    """Reset token for open platform API access"""
    # Verify access_key exists
    credentials = await get_credentials(access_key, session)
    if not credentials:
        raise CustomAgentException(
            error_code=ErrorCode.INVALID_PARAMETERS,
            message="Invalid access key"
        )
    
    # Generate new token
    return await generate_token(access_key, session)

async def get_token(access_key: str, session: AsyncSession) -> Optional[str]:
    """Get stored token for access key"""
    credentials = await get_credentials(access_key, session)
    if not credentials or not credentials.token:
        return None
    
    # Token is already encrypted, no need for additional decryption
    return credentials.token

async def verify_stored_token(access_key: str, token: str, session: AsyncSession) -> bool:
    """Verify if provided token matches the stored token"""
    stored_token = await get_token(access_key, session)
    if not stored_token:
        return False
    
    return stored_token == token 
