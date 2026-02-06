"""
ClawBots Gateway - MCP Server & Adapters

The universal entry point for AI agents to connect to the platform.
"""

from .mcp_server import MCPServer, Location, AgentInfo, WorldEvent
from .websocket import WebSocketAdapter, WebSocketSession

__all__ = [
    "MCPServer",
    "Location",
    "AgentInfo", 
    "WorldEvent",
    "WebSocketAdapter",
    "WebSocketSession"
]
