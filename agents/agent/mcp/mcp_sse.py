"""
MCP (Model Context Protocol) Server implementation
"""

import logging
import uuid
from contextvars import ContextVar
from typing import Callable, Awaitable

from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from mcp.server.sse import SseServerTransport
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from starlette.routing import Route, Mount

from agents.models.models import (
    MCPServer,
    MCPTool,
)
from agents.services.assistant_mcp_service import (
    get_assistant_mcp_service,
    get_single_assistant_mcp_service
)
from agents.services.mcp_service import get_coin_api_mcp_service, _create_server_instance
from agents.utils.session import get_async_session_ctx, get_user_from_request

logger = logging.getLogger(__name__)
ctx_correlation_id = ContextVar("correlation_id", default="")

transport = SseServerTransport("/messages/")

async def handle_mcp_request(
    request: Request,
    service_name: str,
    get_service_func: Callable[..., Awaitable[Server]],
    *args,
    **kwargs
) -> Response:
    """Generic handler for MCP requests"""
    correlation_id = str(uuid.uuid4())
    ctx_correlation_id.set(correlation_id)
    logger.info(f"[{correlation_id}] Received {service_name} service request: {request.method} {request.url.path}?{request.url.query}")
    
    try:
        # Get user information
        user = await get_user_from_request(request)
        if not user:
            return JSONResponse({"error": "Invalid API key"}, status_code=401)
        
        # Get MCP service instance
        mcp_service = await get_service_func(user, *args, **kwargs)
        
        # Connect SSE and process request
        async with transport.connect_sse(
                request.scope, request.receive, request._send
        ) as streams:
            await mcp_service.run(
                streams[0],
                streams[1],
                InitializationOptions(
                    server_name=service_name,
                    server_version="0.1.0",
                    capabilities=mcp_service.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={
                            "user": user
                        },
                    ),
                ),
            )
        
        logger.info(f"[{correlation_id}] {service_name} service request processing completed")
        return Response(status_code=200)
    except Exception as e:
        logger.exception(f"[{correlation_id}] Error occurred while processing {service_name} request: {str(e)}")
        return Response(f"Error occurred while processing request: {str(e)}", status_code=500)

async def handle_coin_api_sse(request: Request):
    """Handle requests for the built-in coin-api service"""
    return await handle_mcp_request(request, "coin-api", get_coin_api_mcp_service)

async def handle_assistant_api_sse(request: Request):
    """Handle requests for the assistant-api service"""
    return await handle_mcp_request(request, "assistant-api", get_assistant_mcp_service)

async def handle_single_assistant_api_sse(request: Request):
    """Handle requests for a specific assistant's MCP service"""
    assistant_id = request.path_params.get("assistant_id")
    if not assistant_id:
        return JSONResponse(
            {"error": "Missing assistant ID"},
            status_code=400
        )
    return await handle_mcp_request(
        request,
        f"assistant-{assistant_id}-api",
        get_single_assistant_mcp_service,
        assistant_id
    )

async def handle_dynamic_mcp(request: Request):
    """Handle requests for dynamically created MCP services"""
    correlation_id = str(uuid.uuid4())
    ctx_correlation_id.set(correlation_id)
    
    # Extract MCP service name from path
    mcp_name = request.path_params.get("mcp_name", "")
    logger.info(f"[{correlation_id}] Received dynamic MCP service request: {request.method} {request.url.path}?{request.url.query}")
    
    try:
        # Extract user information from the request
        user = await get_user_from_request(request)
            
        # Check if MCP service exists in the database
        async with get_async_session_ctx() as session:
            result = await session.execute(
                select(MCPServer)
                .options(selectinload(MCPServer.tools).selectinload(MCPTool.tool))
                .where(MCPServer.name == mcp_name)
            )
            server = result.scalar_one_or_none()
            
            if not server:
                logger.warning(f"[{correlation_id}] MCP service '{mcp_name}' not found")
                return JSONResponse(
                    {"error": f"MCP service '{mcp_name}' not found"},
                    status_code=404
                )

            # Create MCP server instance
            mcp_server = await _create_server_instance(mcp_name, user)

            # Connect SSE and process request
            async with transport.connect_sse(
                    request.scope, request.receive, request._send
            ) as streams:
                await mcp_server.run(
                    streams[0],
                    streams[1],
                    InitializationOptions(
                        server_name=mcp_name,
                        server_version="0.1.0",
                        capabilities=mcp_server.get_capabilities(
                            notification_options=NotificationOptions(),
                            experimental_capabilities={},
                        ),
                    ),
                )
        
        logger.info(f"[{correlation_id}] Dynamic MCP service '{mcp_name}' request processing completed")
        return Response(status_code=200)
    except Exception as e:
        logger.exception(f"[{correlation_id}] Error occurred while processing dynamic MCP service '{mcp_name}' request: {str(e)}")
        return Response(f"Error occurred while processing request: {str(e)}", status_code=500)

def get_all_routes():
    """Create all routes"""
    routes = [
        Route("/mcp/coin-api", endpoint=handle_coin_api_sse, methods=["GET"]),
        Route("/mcp/coin-api", endpoint=handle_coin_api_sse, methods=["POST"]),
        Route("/mcp/assistant-api", endpoint=handle_assistant_api_sse, methods=["GET", "POST"]),
        Route("/mcp/assistant/{assistant_id}", endpoint=handle_single_assistant_api_sse, methods=["GET", "POST"]),
        Route("/mcp/{mcp_name:path}", endpoint=handle_dynamic_mcp, methods=["GET", "POST"]),
        Mount("/messages/", app=transport.handle_post_message),
    ]
    return routes

def get_application():
    """Create Starlette application"""
    routes = get_all_routes()
    return Starlette(routes=routes)

# Create application instance
application = get_application()
