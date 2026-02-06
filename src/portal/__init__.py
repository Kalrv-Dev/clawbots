"""
ClawBots Portal Module

Agent templates, registration wizards, and setup utilities.
"""

from .config import PortalConfig, AgentSetup, AvatarSetup

__all__ = ["PortalConfig", "AgentSetup", "AvatarSetup"]

# Global portal instance
_portal = None

def get_portal() -> PortalConfig:
    """Get or create the global portal instance."""
    global _portal
    if _portal is None:
        _portal = PortalConfig()
    return _portal
