import logging
import uuid
from typing import Dict, List, Any, Optional

import mcp.types as types
from mcp.server import Server
from sqlalchemy import select, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from agents.exceptions import CustomAgentException, ErrorCode
from agents.models.models import App
from agents.utils.session import get_async_session_ctx

logger = logging.getLogger(__name__)

async def create_assistant_mcp_server(user: dict, session: AsyncSession) -> Server:
    """
    Create an MCP server instance for the user's assistants
    
    Args:
        user: User information
        session: Database session
        
    Returns:
        Server instance configured with handlers
    """
    # Create a new server instance
    server = Server("assistant-api")
    
    # Register tool list handler
    @server.list_tools()
    async def handle_list_tools() -> List[types.Tool]:
        """List available assistants as tools"""
        try:
            # Get user's apps from database
            query = select(App).where(
                or_(
                    App.tenant_id == user.get("tenant_id"),
                    App.is_public == True
                )
            )
            result = await session.execute(query)
            apps = result.scalars().all()
            
            # Convert apps to MCP tools
            tools = []
            for app in apps:
                tools.append(types.Tool(
                    name=f"chat-with-{app.id}",
                    description=f"{app.description}",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "message": {
                                "type": "string",
                                "description": "Message to send to the assistant"
                            },
                            "conversation_id": {
                                "type": "string",
                                "description": "Optional conversation ID to continue a previous dialogue",
                                "required": False
                            }
                        },
                        "required": ["message"]
                    }
                ))
            
            return tools
        except Exception as e:
            logger.error(f"Error listing assistants: {e}", exc_info=True)
            return []
    
    # Register tool call handler
    @server.call_tool()
    async def handle_call_tool(name: str, arguments: Dict[str, Any] = None) -> list[types.TextContent | types.ImageContent]:
        """Handle assistant chat requests"""
        try:
            if not name.startswith("chat-with-"):
                return [types.TextContent(type="text", text=f"Unknown tool: {name}")]
                
            # Extract app ID from tool name
            app_id = name[10:]  # Remove "chat-with-" prefix
            
            # Get app from database
            query = select(App).where(
                or_(
                    App.tenant_id == user.get("tenant_id"),
                    App.is_public == True
                ),
                App.id == app_id
            )
            result = await session.execute(query)
            app = result.scalar_one_or_none()
            
            if not app:
                return [types.TextContent(type="text", text=f"Assistant not found: {app_id}")]
            
            # Prepare dialogue request
            from agents.protocol.schemas import DialogueRequest
            dialogue_request = DialogueRequest(
                query=arguments.get("message", ""),
                conversationId=arguments.get("conversation_id", str(uuid.uuid4())),
                initFlag=arguments.get("init_flag", False)
            )
            
            # Call agent service for dialogue
            from agents.services import agent_service
            response_stream = agent_service.dialogue(app_id, dialogue_request, user, session)
            
            # Convert stream to list
            response_list = []
            async for chunk in response_stream:
                response_list.append(types.TextContent(type="text", text=f"{chunk}"))
            
            return response_list
            
        except Exception as e:
            logger.error(f"Error in assistant chat: {e}", exc_info=True)
            return [types.TextContent(type="text", text=f"Error in assistant chat: {str(e)}")]
    
    return server

async def get_assistant_mcp_service(user: dict, session: Optional[AsyncSession] = None) -> Server:
    """
    Get or create an MCP server instance for the user's assistants
    
    Args:
        user: User information
        session: Optional database session
        
    Returns:
        Server instance configured with handlers
    """
    # If a session is provided, use it directly
    if session:
        return await create_assistant_mcp_server(user, session)
    
    # Otherwise use context manager to ensure session is properly closed
    try:
        async with get_async_session_ctx() as managed_session:
            return await create_assistant_mcp_server(user, managed_session)
    except Exception as e:
        logger.error(f"Error creating assistant MCP service: {e}", exc_info=True)
        raise CustomAgentException(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to create assistant MCP service: {str(e)}"
        )

async def create_single_assistant_mcp_server(user: dict, session: AsyncSession, assistant_id: str) -> Server:
    """
    Create an MCP server instance for a specific assistant
    
    Args:
        user: User information
        session: Database session
        assistant_id: ID of the specific assistant
        
    Returns:
        Server instance configured with handlers
    """
    # Create a new server instance
    server = Server(f"assistant-{assistant_id}-api")
    
    # Get specific app from database
    from agents.models.models import MCPStore
    query = select(App).join(
        MCPStore,
        App.id == MCPStore.agent_id,
        isouter=True
    ).where(
        or_(
            # Current tenant's apps
            App.tenant_id == user.get("tenant_id"),
            # Public apps
            App.is_public == True,
            # Apps in public MCP stores
            and_(
                MCPStore.is_public == True,
                MCPStore.agent_id == assistant_id
            )
        ),
        App.id == assistant_id,
        App.enable_mcp == True,
    ).distinct()
    
    result = await session.execute(query)
    app = result.scalar_one_or_none()
    
    if not app:
        raise CustomAgentException(
            ErrorCode.INVALID_PARAMETERS,
            f"Assistant not found: {assistant_id}"
        )
    
    # Register tool list handler
    @server.list_tools()
    async def handle_list_tools() -> List[types.Tool]:
        """List available tools for the specific assistant"""
        return [types.Tool(
            name=f"{app.name}",
            description=f"{app.description}",
            inputSchema={
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "Message to send to the assistant"
                    },
                    "conversation_id": {
                        "type": "string",
                        "description": "Optional conversation ID to continue a previous dialogue",
                        "required": False
                    }
                },
                "required": ["message"]
            }
        )]
    
    # Register tool call handler
    @server.call_tool()
    async def handle_call_tool(name: str, arguments: Dict[str, Any] = None) -> list[types.TextContent | types.ImageContent]:
        """Handle assistant chat requests"""
        try:
            # Prepare dialogue request
            from agents.protocol.schemas import DialogueRequest
            dialogue_request = DialogueRequest(
                query=arguments.get("message", ""),
                conversationId=arguments.get("conversation_id", str(uuid.uuid4())),
                initFlag=arguments.get("init_flag", False)
            )
            
            # Call agent service for dialogue
            from agents.services import agent_service
            response_stream = agent_service.dialogue(app.id, dialogue_request, user, session)
            
            # Convert stream to list
            response_list = []
            async for chunk in response_stream:
                response_list.append(types.TextContent(type="text", text=f"{chunk}"))
            
            return response_list
            
        except Exception as e:
            logger.error(f"Error in assistant chat: {e}", exc_info=True)
            return [types.TextContent(type="text", text=f"Error in assistant chat: {str(e)}")]
    
    return server

async def get_single_assistant_mcp_service(user: dict, assistant_id: str, session: Optional[AsyncSession] = None) -> Server:
    """
    Get or create an MCP server instance for a specific assistant
    
    Args:
        user: User information
        assistant_id: ID of the specific assistant
        session: Optional database session
        
    Returns:
        Server instance configured with handlers
    """
    # If a session is provided, use it directly
    if session:
        return await create_single_assistant_mcp_server(user, session, assistant_id)
    
    # Otherwise use context manager to ensure session is properly closed
    try:
        async with get_async_session_ctx() as managed_session:
            return await create_single_assistant_mcp_server(user, managed_session, assistant_id)
    except Exception as e:
        logger.error(f"Error creating single assistant MCP service: {e}", exc_info=True)
        raise CustomAgentException(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to create single assistant MCP service: {str(e)}"
        ) 