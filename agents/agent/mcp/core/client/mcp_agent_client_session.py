"""
MCP agent client session implementation.
"""

from typing import Optional
from datetime import timedelta

from mcp import ClientSession
from mcp.types import CallToolResult, GetPromptResult, ListToolsResult, ListPromptsResult


class MCPAgentClientSession(ClientSession):
    """
    A specialized client session for MCP agents.
    """
    
    def __init__(
        self,
        read_stream,
        write_stream,
        read_timeout: Optional[timedelta] = None,
    ):
        super().__init__(read_stream, write_stream, read_timeout)
        self.server_config = None
    
    async def initialize(self) -> None:
        """Initialize the session."""
        await super().initialize()
    
    async def call_tool(
        self,
        name: str,
        arguments: Optional[dict] = None,
    ) -> CallToolResult:
        """Call a tool by name."""
        return await super().call_tool(name, arguments)
    
    async def get_prompt(
        self,
        name: str,
        arguments: Optional[dict[str, str]] = None,
    ) -> GetPromptResult:
        """Get a prompt by name."""
        return await super().get_prompt(name, arguments)
    
    async def list_tools(self) -> ListToolsResult:
        """List available tools."""
        return await super().list_tools()
    
    async def list_prompts(self) -> ListPromptsResult:
        """List available prompts."""
        return await super().list_prompts() 