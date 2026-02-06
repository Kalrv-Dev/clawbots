"""
ClawBots World Engine

The core simulation engine that manages the virtual world.
"""

from .engine import WorldEngine
from .spatial import SpatialManager
from .events import EventBus
from .embodiment import AvatarManager
from .actions import ActionExecutor

__all__ = [
    "WorldEngine",
    "SpatialManager", 
    "EventBus",
    "AvatarManager",
    "ActionExecutor"
]
