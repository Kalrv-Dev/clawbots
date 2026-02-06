"""
ClawBots World Engine

The core simulation engine that manages the virtual world.
"""

from .engine import WorldEngine, Location, WorldAgent, WorldObject, Region
from .spatial import SpatialManager, Vector3, SpatialGrid, SpatialEntity
from .events import EventBus, EventType, WorldEvent, EventFilter
from .actions import ActionExecutor, ActionType, ActionResult

__all__ = [
    # Engine
    "WorldEngine",
    "Location", 
    "WorldAgent",
    "WorldObject",
    "Region",
    # Spatial
    "SpatialManager",
    "Vector3",
    "SpatialGrid",
    "SpatialEntity",
    # Events
    "EventBus",
    "EventType",
    "WorldEvent",
    "EventFilter",
    # Actions
    "ActionExecutor",
    "ActionType",
    "ActionResult"
]
