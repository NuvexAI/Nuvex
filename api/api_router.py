import logging

from fastapi import APIRouter, HTTPException, status, FastAPI
from starlette.responses import Response

from agents.common.response import RestResponse
from .image_router import router as image_router
from ..models.db import detect_connection_leaks, get_pool_status, test_connection, initialize_pool

logger = logging.getLogger(__name__)

router = APIRouter()
router.include_router(image_router)

# Add this function to initialize pool on startup
def register_startup_events(app: FastAPI):
    """Register startup events for the application"""
    
    @app.on_event("startup")
    async def initialize_database_pool():
        """Initialize database connection pool on application startup"""
        logger.info("Application starting, initializing database connection pool...")
        pool_init_result = await initialize_pool()
        
        status = pool_init_result.get("status", "unknown")
        if status == "failed":
            error_msg = pool_init_result.get("details", {}).get("error", "Unknown error")
            logger.error(f"❌ Database connection pool initialization failed: {error_msg}")
            # We don't want to stop the application, but log this as a critical issue
            logger.critical("Database pool initialization failed - API may experience issues!")
        elif status == "warning":
            warning_msg = pool_init_result.get("details", {}).get("session_error", "Unknown warning")
            logger.warning(f"⚠️ Database connection pool initialization has warnings: {warning_msg}")
            logger.info("Despite warnings, API will continue to run but may experience database issues")
        else:  # ready or unknown
            # Get connection pool statistics
            pool_status = pool_init_result.get("details", {}).get("pool_status", {})
            # Log MySQL connection information (if available)
            mysql_stats = pool_status.get("mysql_stats", {})
            if mysql_stats:
                connections = mysql_stats.get("Connections", "unknown")
                threads = mysql_stats.get("Threads_connected", "unknown")
                max_used = mysql_stats.get("Max_used_connections", "unknown")
                logger.info(f"✅ Database connection pool initialized successfully - Connections: {connections}, Current threads: {threads}, Max used connections: {max_used}")
            else:
                logger.info("✅ Database connection pool initialized successfully, but unable to get MySQL statistics")
            
            # Log warm connections information
            warm_conn = pool_init_result.get("details", {}).get("warm_connections", 0)
            logger.info(f"Successfully created {warm_conn} warm connections for pool")

@router.options("/{full_path:path}")
async def preflight_handler(full_path: str):
    return Response(status_code=204)  # 204 No Content


async def health_check():
    """
    Health check endpoint that returns service status
    Checks service status including database connection pool status
    """
    try:
        # First perform connection test
        conn_test = await test_connection()
        
        if conn_test.get("connection") != "success":
            # Connection test failed, return 503 Service Unavailable
            logger.warning(f"Health check failed: Database connection test failed - {conn_test.get('error', 'Unknown error')}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Database connection test failed: {conn_test.get('error', 'Unknown error')}"
            )
        
        # Get connection pool status and check for leaks
        leak_detected = await detect_connection_leaks(threshold_percentage=90)
        
        if leak_detected:
            # Connection leak detected, return 503 Service Unavailable
            logger.warning("Health check failed: Database connection pool usage is high")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database connection pool usage is high, possible connection leak detected"
            )
        
        # All good, return success status
        return RestResponse(data={"status": "ok", "database_connection": "ok"})
    except HTTPException:
        # Re-raise HTTPException directly
        raise
    except Exception as e:
        # Other exceptions return 500 error
        logger.error(f"Health check failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Health check failed: {str(e)}"
        )


@router.get("/")
async def root():
    """Root endpoint that returns service status"""
    return await health_check()


@router.get("/api/health")
async def health():
    """Health check endpoint"""
    return await health_check()


@router.get("/api/health/detailed")
async def health_detailed():
    """Detailed health check endpoint, includes database connection pool status details"""
    try:
        # First perform connection test
        conn_test = await test_connection()
        
        # Get pool status from connection test
        pool_status = conn_test.get("pool_status", await get_pool_status())
        
        # Check connection pool usage
        usage_percentage = pool_status.get("usage_percentage", 0)
        active_connections = pool_status.get("active_connections", 0)
        total_capacity = pool_status.get("total_capacity", 50)
        
        # Check connection test and pool status to determine health
        connection_ok = conn_test.get("connection") == "success"
        is_pool_warning = usage_percentage >= 70
        
        # Build response data
        response_data = {
            "status": "warning" if is_pool_warning else ("error" if not connection_ok else "ok"),
            "database": {
                "connection_test": {
                    "success": connection_ok,
                    "response_time_ms": conn_test.get("test_time_ms", 0),
                    "test_value": conn_test.get("test_value"),
                    "error": conn_test.get("error") if not connection_ok else None
                },
                "pool_status": {
                    "pool_type": pool_status.get("pool_type", "unknown"),
                    "active_connections": active_connections,
                    "total_capacity": total_capacity,
                    "usage_percentage": usage_percentage,
                    "checkout_total": pool_status.get("total_checkouts", 0),
                    "checkin_total": pool_status.get("total_checkins", 0),
                    "checkout_errors": pool_status.get("checkout_errors", 0),
                    "pool_size": pool_status.get("pool_size", 20),
                    "max_overflow": pool_status.get("max_overflow", 30)
                },
                "mysql_stats": pool_status.get("mysql_stats", {}),
                "alert": "Database connection pool usage is high or connection timeout" if is_pool_warning else (
                    "Database connection test failed" if not connection_ok else None
                )
            }
        }
        
        # If connection test failed or pool status is poor, return 503 status code
        if not connection_ok or is_pool_warning:
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            logger.warning(f"Detailed health check: Database status abnormal - {response_data['database']['alert']}")
            raise HTTPException(
                status_code=status_code,
                detail=response_data
            )
        
        # Return normal response
        return RestResponse(data=response_data)
    except HTTPException:
        # Re-raise HTTPException directly
        raise
    except Exception as e:
        # Other exceptions return 500 error
        logger.error(f"Detailed health check failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Detailed health check failed: {str(e)}"
        )
