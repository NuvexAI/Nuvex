"""
Client session generator implementation.
"""

from typing import AsyncGenerator, Optional
from datetime import timedelta

from mcp import ClientSession, stdio_client
from mirascope.mcp import sse_client

from ..client.transport.websocket import websocket_client


async def gen_client(
    server_name: str,
    server_registry: "ServerRegistry",
    client_session_factory: type[ClientSession] = ClientSession,
    read_timeout: Optional[timedelta] = None,
) -> AsyncGenerator[ClientSession, None]:
    """
    Generate a client session for the specified server.
    
    Args:
        server_name: The name of the server to connect to
        server_registry: The server registry to use
        client_session_factory: The client session factory to use
        read_timeout: Optional read timeout for the session
        
    Returns:
        An async generator yielding a client session
    """
    server_config = server_registry.get_server_config(server_name)
    
    if server_config.transport == "stdio":
        transport_context = stdio_client(
            command=server_config.command,
            args=server_config.args,
            env=server_config.env,
            cwd=server_config.cwd,
        )
    elif server_config.transport == "sse":
        transport_context = sse_client(server_config.url)
    elif server_config.transport == "websocket":
        transport_context = websocket_client(server_config.url)
    else:
        raise ValueError(f"Unknown transport type: {server_config.transport}")
    
    async with transport_context as (read_stream, write_stream):
        session = client_session_factory(
            read_stream=read_stream,
            write_stream=write_stream,
            read_timeout=read_timeout,
        )
        
        try:
            yield session
        finally:
            await session.close() 