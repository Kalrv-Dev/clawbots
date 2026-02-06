"""
ClawBots Registry - Agent Authentication & Identity

Manages agent registration, authentication, and permissions.
"""

from .auth import AuthManager
from .agents import AgentRegistry

__all__ = ["AuthManager", "AgentRegistry"]
