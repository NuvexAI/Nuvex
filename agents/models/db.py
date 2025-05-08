import asyncio
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime
from urllib.parse import quote

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, AsyncEngine
from sqlalchemy.orm import sessionmaker

from agents.common.config import SETTINGS
from agents.models.models import Base

logger = logging.getLogger(__name__)

DATABASE_URL = f"mysql+aiomysql://{SETTINGS.MYSQL_USER}:{quote(SETTINGS.MYSQL_PASSWORD)}@{SETTINGS.MYSQL_HOST}:{SETTINGS.MYSQL_PORT}/{SETTINGS.MYSQL_DB}"

# Configure database connection pool
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # Set to False in production environment
    pool_size=20,  # Increased pool size from 10 to 20
    max_overflow=30,  # Increased max overflow connections from 20 to 30
    pool_timeout=30,  # Timeout for getting connections (unchanged)
    pool_recycle=300,  # Reduced connection recycling time from 600s to 300s (5 minutes)
    pool_pre_ping=True,  # Test connection validity before use
    # Set connection parameters
    connect_args={
        "charset": "utf8mb4",
        "use_unicode": True,
        "connect_timeout": 10  # Connection timeout in seconds
        # Removed read_timeout and write_timeout as they're not supported by aiomysql
    }
)

# Global connection pool statistics
pool_stats = {
    "active_connections": 0,
    "total_checkouts": 0,
    "total_checkins": 0,
    "checkout_errors": 0
}

# Setup connection pool event listeners
@event.listens_for(engine.sync_engine, "checkout")
def on_checkout(dbapi_conn, conn_record, conn_proxy):
    """Triggered when a connection is checked out from the pool"""
    pool_stats["active_connections"] += 1
    pool_stats["total_checkouts"] += 1
    logger.debug(f"Connection checkout: active={pool_stats['active_connections']}")

@event.listens_for(engine.sync_engine, "checkin")
def on_checkin(dbapi_conn, conn_record):
    """Triggered when a connection is returned to the pool"""
    if pool_stats["active_connections"] > 0:  # Prevent counting errors resulting in negative values
        pool_stats["active_connections"] -= 1
    pool_stats["total_checkins"] += 1
    logger.debug(f"Connection checkin: active={pool_stats['active_connections']}")

# Create session factory
SessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Avoid reloading objects after commit
    autocommit=False,
    autoflush=False
)

def get_async_engine() -> AsyncEngine:
    """
    Get the async database engine instance
    
    Returns:
        AsyncEngine: The async SQLAlchemy engine
    """
    return engine

@asynccontextmanager
async def get_session():
    """Provide a transactional scope around a series of operations."""
    session = SessionLocal()
    start_time = asyncio.get_event_loop().time()
    transaction_timeout = 45  # Reduced transaction timeout from 60s to 45s
    
    try:
        yield session
        
        # Check if transaction took too long
        elapsed = asyncio.get_event_loop().time() - start_time
        if elapsed > transaction_timeout:
            logger.warning(f"Transaction took too long: {elapsed:.2f}s, consider optimizing")
            
        await session.commit()
        
    except Exception as e:
        logger.error(f"Database error in transaction: {str(e)}", exc_info=True)
        await session.rollback()
        raise
    finally:
        await session.close()
        logger.debug(f"Session closed after {asyncio.get_event_loop().time() - start_time:.2f}s")

async def get_db():
    """Dependency for providing database session for each request."""
    session = None
    start_time = asyncio.get_event_loop().time()
    request_timeout = 30  # Set database operation timeout to 30 seconds
    
    try:
        session = SessionLocal()
        yield session
        
        # Check if request took too long
        elapsed = asyncio.get_event_loop().time() - start_time
        if elapsed > request_timeout:
            logger.warning(f"Database operation took too long: {elapsed:.2f}s")
            
        await session.commit()
        
    except Exception as e:
        logger.error(f"Database error in request: {str(e)}", exc_info=True)
        if session:
            await session.rollback()
        # Increment error counter since we can't use the event listener
        pool_stats["checkout_errors"] += 1
        raise
    finally:
        if session:
            await session.close()
            logger.debug(f"Request DB session closed after {asyncio.get_event_loop().time() - start_time:.2f}s")

async def init_db(engine: AsyncEngine):
    """Initialize database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def dispose_engine():
    """Properly dispose of the engine and its connection pool."""
    try:
        await engine.dispose()
    except Exception as e:
        logger.error(f"Error disposing database engine: {str(e)}", exc_info=True)

async def get_pool_status():
    """
    Get database connection pool status information
    
    Uses SQLAlchemy public API and event statistics
    
    Returns:
        dict: Connection pool status information
    """
    try:
        pool = engine.pool
        
        # Create basic info dictionary
        pool_info = {
            "pool_type": f"{pool.__class__.__name__}"
        }
        
        # Use public API to get basic configuration - properly handle methods vs attributes
        try:
            # Get pool size - could be method or attribute
            if hasattr(pool, "size"):
                try:
                    # Check if it's a callable (method)
                    if callable(pool.size):
                        pool_info["pool_size"] = pool.size()
                    else:
                        pool_info["pool_size"] = pool.size
                except Exception:
                    pool_info["pool_size"] = 20  # Default
            else:
                pool_info["pool_size"] = 20  # Default
                
            # Get max_overflow - could be a different name or not exist
            for attr_name in ["max_overflow", "_max_overflow", "overflow"]:
                if hasattr(pool, attr_name):
                    try:
                        attr_val = getattr(pool, attr_name)
                        if callable(attr_val):
                            pool_info["max_overflow"] = attr_val()
                        else:
                            pool_info["max_overflow"] = attr_val
                        break
                    except Exception:
                        pass
            
            if "max_overflow" not in pool_info:
                pool_info["max_overflow"] = 30  # Default
                
            # Get other config attributes safely
            for attr_name in ["timeout", "recycle"]:
                if hasattr(pool, attr_name):
                    try:
                        attr_val = getattr(pool, attr_name)
                        if callable(attr_val):
                            pool_info[attr_name] = attr_val()
                        else:
                            pool_info[attr_name] = attr_val
                    except Exception:
                        pass
                        
        except Exception as config_err:
            logger.warning(f"Error getting pool configuration: {config_err}")
            # Ensure we have defaults
            if "pool_size" not in pool_info:
                pool_info["pool_size"] = 20
            if "max_overflow" not in pool_info:
                pool_info["max_overflow"] = 30
            
        # Add statistics data from event listeners
        pool_info.update(pool_stats)
        
        # Make sure pool_size and max_overflow are integers, not methods
        pool_size = pool_info.get("pool_size", 20)
        max_overflow = pool_info.get("max_overflow", 30)
        
        # Ensure these are actual integers
        if callable(pool_size):
            try:
                pool_size = pool_size()
            except:
                pool_size = 20
        if callable(max_overflow):
            try:
                max_overflow = max_overflow()
            except:
                max_overflow = 30
                
        # Update with properly processed values
        pool_info["pool_size"] = pool_size
        pool_info["max_overflow"] = max_overflow
        
        # Calculate total capacity and usage percentage
        total_capacity = int(pool_size) + int(max_overflow)
        active_connections = pool_info.get("active_connections", 0)
        
        pool_info["total_capacity"] = total_capacity
        pool_info["total_used"] = active_connections
        
        # Calculate usage percentage
        if total_capacity > 0:
            pool_info["usage_percentage"] = round((active_connections / total_capacity) * 100, 2)
        else:
            pool_info["usage_percentage"] = 0
            
        # Get database connection information (MySQL)
        try:
            # Use a separate connection instead of reusing any potentially problematic one
            # Create a fresh connection directly
            async with engine.connect() as conn:
                # Simple test query first
                await conn.execute(text("SELECT 1"))
                
                # Only then try to get MySQL statistics
                try:
                    result = await conn.execute(text("""
                        SHOW STATUS WHERE Variable_name IN (
                            'Threads_connected', 
                            'Max_used_connections',
                            'Connection_errors_max_connections',
                            'Aborted_connects',
                            'Connections'
                        )
                    """))
                    
                    # Get all rows immediately to avoid ResourceClosedError
                    # Different SQLAlchemy versions handle this differently
                    try:
                        # Try simple direct access first
                        rows = result.all()
                    except (AttributeError, TypeError):
                        try:
                            # Then try await (older SQLAlchemy)
                            rows = await result.fetchall()
                        except (TypeError, AttributeError):
                            # Finally fallback to non-await for newer SQLAlchemy
                            rows = result.fetchall()
                    
                    # Convert to dictionary
                    db_stats = {row[0]: row[1] for row in rows}
                    pool_info["mysql_stats"] = db_stats
                except Exception as stats_err:
                    logger.warning(f"Failed to get detailed MySQL statistics: {stats_err}")
                    pool_info["mysql_stats"] = {"error": str(stats_err)}
        except Exception as db_err:
            logger.warning(f"Failed to get MySQL connection statistics: {db_err}")
            pool_info["mysql_stats"] = {}
            
        # Log status for analysis
        logger.info(f"Connection pool status: usage={pool_info.get('usage_percentage')}%, "
                    f"active connections={pool_info.get('active_connections')}, "
                    f"total capacity={total_capacity}")
        
        return pool_info
    except Exception as e:
        logger.error(f"Error getting pool status: {str(e)}", exc_info=True)
        return {
            "error": str(e),
            "pool_type": str(getattr(engine.pool, "__class__", {"__name__": "unknown"}))
        }

async def detect_connection_leaks(threshold_percentage=80):
    """
    Detect potential connection leaks in the database pool
    
    Logs detailed connection pool status and stack trace when usage exceeds threshold
    
    Args:
        threshold_percentage: Connection usage percentage threshold to trigger warnings
    
    Returns:
        bool: True if potential leak detected, False otherwise
    """
    try:
        pool_status = await get_pool_status()
        
        # Check for errors
        if "error" in pool_status:
            logger.error(f"Cannot detect leaks: {pool_status['error']}")
            return False
        
        # Use the pre-calculated usage percentage and capacities
        usage_percentage = pool_status.get("usage_percentage", 0)
        active_connections = pool_status.get("active_connections", 0)
        total_capacity = pool_status.get("total_capacity", 50)
        
        # Check if threshold has been reached
        logger.info(f"detect_connection_leaks usage_percentage={usage_percentage} "
                   f"total_used={active_connections} total_capacity={total_capacity}")
        
        if usage_percentage >= threshold_percentage:
            # Log detailed pool status
            logger.warning(
                f"Possible connection leak detected! "
                f"Connection usage: {usage_percentage:.1f}% "
                f"({active_connections}/{total_capacity}). "
                f"Pool status: {pool_status}"
            )
            
            # Add more debug information
            import traceback
            current_stack = ''.join(traceback.format_stack())
            logger.info(f"Stack trace when leak detected:\n{current_stack}")
            
            return True
        return False
    except Exception as e:
        logger.error(f"Error in leak detection: {str(e)}", exc_info=True)
        return False

async def test_connection():
    """
    Test database connection and get connection pool status
    """
    session = None
    start_time = time.time()
    try:
        # Create new session
        session = SessionLocal()
        
        # Execute simple query and get results immediately
        query = "SELECT 1 as test_value"
        try:
            result = await session.execute(text(query))
            # Get value immediately to avoid result object closed issues
            try:
                row = result.first()
                test_value = row[0] if row else None
            except Exception as fetch_err:
                logger.warning(f"Error fetching result using first(): {fetch_err}")
                # Try alternative methods
                try:
                    row = result.one()
                    test_value = row[0] if row else None
                except Exception:
                    # Finally try scalar method
                    try:
                        test_value = result.scalar()
                    except Exception as scalar_err:
                        logger.warning(f"All result fetching methods failed: {scalar_err}")
                        test_value = None
            
            # Ensure result is fully fetched to avoid closed result object issues in subsequent operations
            result = None  # Release result object reference
            
            # Calculate response time
            response_time = time.time() - start_time
            
            # Get pool status after successful connection
            pool_status = await get_pool_status()
            
            return {
                "connection": "success",
                "test_value": test_value,
                "test_time_ms": round(response_time * 1000, 2),  # In milliseconds
                "pool_status": pool_status
            }
        except Exception as ex:
            logger.error(f"Database query failed: {ex}")
            # Calculate response time
            response_time = time.time() - start_time
            
            # Try to get pool status even in case of connection failure
            try:
                pool_status = await get_pool_status()
            except Exception as pool_ex:
                logger.error(f"Failed to get pool status after connection error: {pool_ex}")
                pool_status = {"error": str(pool_ex)}
                
            return {
                "connection": "failed",
                "error": str(ex),
                "test_time_ms": round(response_time * 1000, 2),  # In milliseconds
                "pool_status": pool_status
            }
    except Exception as ex:
        # Calculate response time
        response_time = time.time() - start_time
        
        logger.error(f"Database session creation failed: {ex}")
        return {
            "connection": "failed",
            "error": str(ex),
            "test_time_ms": round(response_time * 1000, 2),  # In milliseconds
            "pool_status": {"error": "Unable to get pool status, session creation failed"}
        }
    finally:
        # Ensure session is always closed
        if session:
            try:
                await session.close()
            except Exception as close_err:
                logger.error(f"Error closing session: {close_err}")

# Initialize database on application startup
if __name__ == '__main__':
    async def init():
        try:
            await init_db(engine)
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database: {str(e)}", exc_info=True)
        finally:
            await dispose_engine()
    
    asyncio.run(init())

# Add a function to initialize the connection pool
async def initialize_pool():
    """
    Initialize and pre-warm the database connection pool
    """
    logger.info("Initializing database connection pool...")
    pool_info = {
        "status": "unknown",
        "timestamp": datetime.now().isoformat(),
        "details": {}
    }
    
    # Validate database configuration
    try:
        # 1. Try direct connection creation
        logger.info("Testing direct database connection...")
        async with engine.connect() as conn:
            try:
                # Execute simple test query
                await conn.execute(text("SELECT 1"))
                logger.info("✅ Basic database connection successful")
                pool_info["details"]["basic_connection"] = "success"
            except Exception as conn_err:
                # Connection failed
                error_msg = f"❌ Failed to establish basic database connection: {conn_err}"
                logger.error(error_msg)
                pool_info["status"] = "failed"
                pool_info["details"]["basic_connection"] = "failed"
                pool_info["details"]["error"] = str(conn_err)
                return pool_info
    
        # 2. Try connection test through session system
        logger.info("Testing database session system...")
        try:
            conn_test = await test_connection()
            if conn_test.get("connection") == "success":
                logger.info("✅ Database session test successful")
                pool_info["details"]["session_test"] = "success"
                # Get connection pool status information
                pool_info["details"]["pool_status"] = conn_test.get("pool_status", {})
                pool_info["status"] = "ready"
            else:
                logger.warning(f"⚠️ Database session test failed: {conn_test.get('error', 'Unknown error')}")
                pool_info["details"]["session_test"] = "failed"
                pool_info["details"]["session_error"] = conn_test.get("error", "Unknown error")
                pool_info["status"] = "warning" 
        except Exception as session_err:
            logger.warning(f"⚠️ Error during session test: {session_err}")
            pool_info["details"]["session_test"] = "error"
            pool_info["details"]["session_error"] = str(session_err)
            pool_info["status"] = "warning"
    
        # 3. Pre-warm connection pool - create several connections
        logger.info("Pre-warming connection pool...")
        warm_connections = []
        success_count = 0
        try:
            # Try to create 3 connections for warm-up
            for i in range(3):
                try:
                    conn = await engine.connect()
                    await conn.execute(text("SELECT 1"))
                    warm_connections.append(conn)
                    success_count += 1
                except Exception as warm_err:
                    logger.warning(f"Failed to create warm connection #{i+1}: {warm_err}")
            
            # Log warm-up results
            logger.info(f"✅ Created {success_count}/3 warm connections successfully")
            pool_info["details"]["warm_connections"] = success_count
        except Exception as warm_err:
            logger.warning(f"Error during pool warming: {warm_err}")
            pool_info["details"]["warm_error"] = str(warm_err)
        finally:
            # Release warm connections
            for conn in warm_connections:
                try:
                    await conn.close()
                except Exception:
                    pass
    
        # If at least basic connection successful, set status as ready
        if pool_info["status"] == "unknown":
            pool_info["status"] = "ready"
            
        return pool_info
        
    except Exception as e:
        error_msg = f"❌ Database pool initialization failed: {e}"
        logger.error(error_msg)
        pool_info["status"] = "failed"
        pool_info["details"]["error"] = str(e)
        return pool_info
