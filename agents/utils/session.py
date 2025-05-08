"""
Session and user information handling utilities
"""

import asyncio
import inspect
import logging
from contextlib import asynccontextmanager
from typing import Optional

from starlette.requests import Request

from agents.services import verify_token_and_get_credentials

logger = logging.getLogger(__name__)

async def get_async_session():
    """
    Get asynchronous database session
    
    Returns:
        Asynchronous database session
        
    Warning:
        This function does not automatically close the session.
        Prefer using get_async_session_ctx() to ensure the session is properly closed.
        Direct usage of this function may lead to connection leaks.
    """
    from agents.models.db import get_async_engine
    from sqlalchemy.ext.asyncio import AsyncSession
    
    engine = get_async_engine()
    async_session = AsyncSession(engine, expire_on_commit=False)
    
    # Add warning log to remind developers that this function doesn't automatically close the connection
    # Check the call stack, don't log warning if called from get_async_session_ctx
    caller_frame = inspect.currentframe().f_back
    caller_func_name = caller_frame.f_code.co_name if caller_frame else "unknown"
    
    if caller_func_name != "get_async_session_ctx":
        logger.warning(
            "get_async_session() called directly - ensure you manually close this session "
            "or use get_async_session_ctx() context manager instead to prevent connection leaks"
        )
    
    return async_session

@asynccontextmanager
async def get_async_session_ctx():
    """
    Get database session supporting asynchronous context manager protocol
    
    Usage:
    async with get_async_session_ctx() as session:
        # Perform operations with session
    
    Returns:
        Database session supporting asynchronous context manager
    """
    from agents.models.db import get_async_engine
    from sqlalchemy.ext.asyncio import AsyncSession
    
    # Create session directly instead of through get_async_session() to avoid unnecessary warning logs
    engine = get_async_engine()
    session = AsyncSession(engine, expire_on_commit=False)
    
    start_time = asyncio.get_event_loop().time()
    
    try:
        yield session
        await session.commit()
    except Exception as e:
        # Log specific exception details for debugging
        logger.error(f"Exception in database session: {str(e)}", exc_info=True)
        await session.rollback()
        raise
    finally:
        await session.close()
        elapsed = asyncio.get_event_loop().time() - start_time
        logger.debug(f"Session closed after {elapsed:.2f}s")

async def get_user_from_request(request: Request) -> Optional[dict]:
    """
    Extract user information from request
    
    Args:
        request: Starlette request object
        
    Returns:
        User information dictionary
    """
    token = request.query_params.get("api-key")
    if not token:
        return None

    try:
        async with get_async_session_ctx() as session:
            credentials = await verify_token_and_get_credentials(token, session)
            return credentials
    except Exception as e:
        logger.error(f"get_user_from_request error, {e}", exc_info=True)
    return None
