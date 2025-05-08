"""
MCP server aggregator implementation.
"""

import asyncio
import logging
from typing import List, Literal, Dict, Optional, TypeVar

from pydantic import BaseModel, ConfigDict
from mcp.client.session import ClientSession
from mcp.types import (
    CallToolResult,
    GetPromptResult,
    ListPromptsResult,
    ListToolsResult,
    Prompt,
    Tool,
    TextContent,
)

from .connection import MCPConnectionManager
from ..client.gen_client import gen_client

logger = logging.getLogger(__name__)

SEP = "_"

# Define type variables for the generalized method
T = TypeVar("T")
R = TypeVar("R")


class NamespacedTool(BaseModel):
    """
    A tool that is namespaced by server name.
    """

    tool: Tool
    server_name: str
    namespaced_tool_name: str


class NamespacedPrompt(BaseModel):
    """
    A prompt that is namespaced by server name.
    """

    prompt: Prompt
    server_name: str
    namespaced_prompt_name: str


class MCPAggregator:
    """
    Aggregates multiple MCP servers. When a developer calls, e.g. call_tool(...),
    the aggregator searches all servers in its list for a server that provides that tool.
    """

    initialized: bool = False
    """Whether the aggregator has been initialized with tools and resources from all servers."""

    connection_persistence: bool = False
    """Whether to maintain a persistent connection to the server."""

    server_names: List[str]
    """A list of server names to connect to."""

    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

    async def __aenter__(self):
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    def __init__(
        self,
        server_names: List[str],
        connection_persistence: bool = True,  # Default to True for better stability
        context: Optional["Context"] = None,
        name: str = None,
        **kwargs,
    ):
        """
        :param server_names: A list of server names to connect to.
        :param connection_persistence: Whether to maintain persistent connections to servers (default: True).
        Note: The server names must be resolvable by the gen_client function, and specified in the server registry.
        """
        self.server_names = server_names
        self.connection_persistence = connection_persistence
        self.agent_name = name
        self._persistent_connection_manager: MCPConnectionManager = None
        self.context = context

        # Maps namespaced_tool_name -> namespaced tool info
        self._namespaced_tool_map: Dict[str, NamespacedTool] = {}
        # Maps server_name -> list of tools
        self._server_to_tool_map: Dict[str, List[NamespacedTool]] = {}
        self._tool_map_lock = asyncio.Lock()

        # Maps namespaced_prompt_name -> namespaced prompt info
        self._namespaced_prompt_map: Dict[str, NamespacedPrompt] = {}
        # Cache for prompt objects, maps server_name -> list of prompt objects
        self._server_to_prompt_map: Dict[str, List[NamespacedPrompt]] = {}
        self._prompt_map_lock = asyncio.Lock()

    async def initialize(self, force: bool = False):
        """Initialize the application."""
        if self.initialized and not force:
            return

        # Keep a connection manager to manage persistent connections for this aggregator
        if self.connection_persistence:
            # Try to get existing connection manager from context
            if not hasattr(self.context, "_mcp_connection_manager_lock"):
                self.context._mcp_connection_manager_lock = asyncio.Lock()

            if not hasattr(self.context, "_mcp_connection_manager_ref_count"):
                self.context._mcp_connection_manager_ref_count = int(0)

            async with self.context._mcp_connection_manager_lock:
                self.context._mcp_connection_manager_ref_count += 1

                if hasattr(self.context, "_mcp_connection_manager"):
                    connection_manager = self.context._mcp_connection_manager
                else:
                    connection_manager = MCPConnectionManager(
                        self.context.server_registry
                    )
                    await connection_manager.__aenter__()
                    self.context._mcp_connection_manager = connection_manager

                self._persistent_connection_manager = connection_manager

        await self.load_servers()
        self.initialized = True

    async def close(self):
        """
        Close all persistent connections when the aggregator is deleted.
        """
        if not self.connection_persistence or not self._persistent_connection_manager:
            return

        try:
            # We only need to manage reference counting if we're using connection persistence
            if hasattr(self.context, "_mcp_connection_manager_lock") and hasattr(
                self.context, "_mcp_connection_manager_ref_count"
            ):
                async with self.context._mcp_connection_manager_lock:
                    # Decrement the reference count
                    self.context._mcp_connection_manager_ref_count -= 1
                    current_count = self.context._mcp_connection_manager_ref_count
                    logger.debug(f"Decremented connection ref count to {current_count}")

                    # Only proceed with cleanup if we're the last user
                    if current_count == 0:
                        logger.info(
                            "Last aggregator closing, shutting down all persistent connections..."
                        )

                        if (
                            hasattr(self.context, "_mcp_connection_manager")
                            and self.context._mcp_connection_manager
                            == self._persistent_connection_manager
                        ):
                            # Add timeout protection for the disconnect operation
                            try:
                                await asyncio.wait_for(
                                    self._persistent_connection_manager.disconnect_all(),
                                    timeout=5.0,
                                )
                            except asyncio.TimeoutError:
                                logger.warning(
                                    "Timeout during disconnect_all(), forcing shutdown"
                                )

                            # Ensure the exit method is called regardless
                            try:
                                await self._persistent_connection_manager.__aexit__(
                                    None, None, None
                                )
                            except Exception as e:
                                logger.error(
                                    f"Error during connection manager __aexit__: {e}"
                                )

                            # Clean up the connection manager from the context
                            delattr(self.context, "_mcp_connection_manager")
                            logger.info(
                                "Connection manager successfully closed and removed from context"
                            )

            self.initialized = False
        except Exception as e:
            logger.error(f"Error during connection manager cleanup: {e}", exc_info=True)
            # Even if there's an error, we should mark ourselves as uninitialized
            self.initialized = False

    async def load_server(self, server_name: str):
        """Load a single server's tools and prompts."""
        try:
            async with gen_client(server_name, self.context.server_registry) as client:
                # Fetch tools
                tools = await self._fetch_tools(client, server_name)
                async with self._tool_map_lock:
                    self._server_to_tool_map[server_name] = tools
                    for tool in tools:
                        self._namespaced_tool_map[tool.namespaced_tool_name] = tool

                # Fetch prompts
                prompts = await self._fetch_prompts(client, server_name)
                async with self._prompt_map_lock:
                    self._server_to_prompt_map[server_name] = prompts
                    for prompt in prompts:
                        self._namespaced_prompt_map[prompt.namespaced_prompt_name] = prompt

        except Exception as e:
            logger.error(f"Error loading server {server_name}: {e}", exc_info=True)
            raise

    async def load_servers(self, force: bool = False):
        """Load all servers' tools and prompts."""
        for server_name in self.server_names:
            await self.load_server(server_name)

    async def get_capabilities(self, server_name: str):
        """Get the capabilities of a server."""
        if self.connection_persistence and self._persistent_connection_manager:
            return await self._persistent_connection_manager.get_server_capabilities(
                server_name
            )
        else:
            async with gen_client(server_name, self.context.server_registry) as client:
                result = await client.initialize()
                return result.capabilities

    async def refresh(self, server_name: str | None = None):
        """Refresh the tools and prompts from the specified server or all servers."""
        if server_name:
            await self.load_server(server_name)
        else:
            await self.load_servers(force=True)

    async def list_servers(self) -> List[str]:
        """List all available servers."""
        return self.server_names

    async def list_tools(self, server_name: str | None = None) -> ListToolsResult:
        """List all available tools."""
        if server_name:
            async with self._tool_map_lock:
                tools = self._server_to_tool_map.get(server_name, [])
                return ListToolsResult(tools=[t.tool for t in tools])
        else:
            async with self._tool_map_lock:
                return ListToolsResult(
                    tools=[t.tool for t in self._namespaced_tool_map.values()]
                )

    async def call_tool(
        self, name: str, arguments: dict | None = None
    ) -> CallToolResult:
        """Call a tool by name."""
        server_name, tool_name = self._parse_capability_name(name, "tool")

        async with self._tool_map_lock:
            if name not in self._namespaced_tool_map:
                raise ValueError(f"Tool {name} not found")

            tool_info = self._namespaced_tool_map[name]

        async def try_call_tool(client: ClientSession):
            return await client.call_tool(tool_name, arguments)

        if self.connection_persistence and self._persistent_connection_manager:
            server_conn = await self._persistent_connection_manager.get_server(
                server_name
            )
            return await try_call_tool(server_conn.session)
        else:
            async with gen_client(server_name, self.context.server_registry) as client:
                return await try_call_tool(client)

    async def list_prompts(self, server_name: str | None = None) -> ListPromptsResult:
        """List all available prompts."""
        if server_name:
            async with self._prompt_map_lock:
                prompts = self._server_to_prompt_map.get(server_name, [])
                return ListPromptsResult(prompts=[p.prompt for p in prompts])
        else:
            async with self._prompt_map_lock:
                return ListPromptsResult(
                    prompts=[p.prompt for p in self._namespaced_prompt_map.values()]
                )

    async def get_prompt(
        self, name: str, arguments: dict[str, str] | None = None
    ) -> GetPromptResult:
        """Get a prompt by name."""
        server_name, prompt_name = self._parse_capability_name(name, "prompt")

        async with self._prompt_map_lock:
            if name not in self._namespaced_prompt_map:
                raise ValueError(f"Prompt {name} not found")

            prompt_info = self._namespaced_prompt_map[name]

        async def try_get_prompt(client: ClientSession):
            return await client.get_prompt(prompt_name, arguments)

        if self.connection_persistence and self._persistent_connection_manager:
            server_conn = await self._persistent_connection_manager.get_server(
                server_name
            )
            return await try_get_prompt(server_conn.session)
        else:
            async with gen_client(server_name, self.context.server_registry) as client:
                return await try_get_prompt(client)

    def _parse_capability_name(
        self, name: str, capability: Literal["tool", "prompt"]
    ) -> tuple[str, str]:
        """Parse a namespaced capability name into server name and capability name."""
        if SEP not in name:
            raise ValueError(
                f"Invalid {capability} name: {name}. Must be in format 'server{SEP}name'"
            )
        server_name, capability_name = name.split(SEP, 1)
        return server_name, capability_name

    async def _fetch_tools(self, client: ClientSession, server_name: str) -> List[Tool]:
        """Fetch tools from a server."""
        result = await client.list_tools()
        return [
            NamespacedTool(
                tool=tool,
                server_name=server_name,
                namespaced_tool_name=f"{server_name}{SEP}{tool.name}",
            )
            for tool in result.tools
        ]

    async def _fetch_prompts(
        self, client: ClientSession, server_name: str
    ) -> List[Prompt]:
        """Fetch prompts from a server."""
        result = await client.list_prompts()
        return [
            NamespacedPrompt(
                prompt=prompt,
                server_name=server_name,
                namespaced_prompt_name=f"{server_name}{SEP}{prompt.name}",
            )
            for prompt in result.prompts
        ] 