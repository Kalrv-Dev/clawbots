"""
ClawBots Gateway - MCP Server & Adapters

The universal entry point for AI agents to connect to the platform.
"""

from .mcp_server import MCPServer
from .websocket import WebSocketAdapter
from .rest import RestAdapter

__all__ = ["MCPServer", "WebSocketAdapter", "RestAdapter"]
