"""
ClawBots World Objects

Interactable objects in the virtual world.
"""

from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import asyncio


class ObjectType(Enum):
    """Types of world objects."""
    FURNITURE = "furniture"      # Chairs, tables, beds
    CONTAINER = "container"      # Chests, boxes, lockers
    DECORATION = "decoration"    # Statues, fountains, plants
    INTERACTIVE = "interactive"  # Buttons, levers, terminals
    VEHICLE = "vehicle"          # Mounts, vehicles
    PORTAL = "portal"            # Teleporters, doors
    VENDOR = "vendor"            # Shops, vending machines
    SIGN = "sign"                # Info boards, signs
    GAME = "game"                # Games, puzzles


@dataclass
class ObjectAction:
    """An action that can be performed on an object."""
    name: str
    description: str
    cooldown: float = 0.0           # Seconds between uses
    requires_proximity: float = 2.0  # Max distance to use
    requires_permission: Optional[str] = None
    animation: Optional[str] = None  # Agent animation to play
    

@dataclass
class WorldObject:
    """
    An interactable object in the world.
    """
    object_id: str
    name: str
    object_type: ObjectType
    description: str = ""
    
    # Position
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    region: str = "main"
    
    # Properties
    actions: List[ObjectAction] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)
    state: Dict[str, Any] = field(default_factory=dict)
    
    # Ownership
    owner_id: Optional[str] = None
    public: bool = True
    
    # Usage tracking
    use_count: int = 0
    last_used: Optional[str] = None
    last_used_by: Optional[str] = None
    
    # Cooldowns per agent
    _cooldowns: Dict[str, float] = field(default_factory=dict)
    
    def can_use(self, agent_id: str, action_name: str, 
                agent_x: float, agent_y: float) -> tuple[bool, str]:
        """Check if agent can use this object's action."""
        # Find action
        action = next((a for a in self.actions if a.name == action_name), None)
        if not action:
            return False, f"Unknown action: {action_name}"
        
        # Check proximity
        distance = ((self.x - agent_x)**2 + (self.y - agent_y)**2)**0.5
        if distance > action.requires_proximity:
            return False, f"Too far away (need to be within {action.requires_proximity}m)"
        
        # Check cooldown
        cooldown_key = f"{agent_id}:{action_name}"
        if cooldown_key in self._cooldowns:
            remaining = self._cooldowns[cooldown_key] - datetime.utcnow().timestamp()
            if remaining > 0:
                return False, f"On cooldown ({remaining:.1f}s remaining)"
        
        # Check ownership/public
        if not self.public and self.owner_id != agent_id:
            return False, "This object is private"
        
        return True, "OK"
    
    def use(self, agent_id: str, action_name: str) -> Dict[str, Any]:
        """Use this object. Returns result."""
        action = next((a for a in self.actions if a.name == action_name), None)
        if not action:
            return {"success": False, "error": "Unknown action"}
        
        # Update tracking
        self.use_count += 1
        self.last_used = datetime.utcnow().isoformat()
        self.last_used_by = agent_id
        
        # Set cooldown
        if action.cooldown > 0:
            cooldown_key = f"{agent_id}:{action_name}"
            self._cooldowns[cooldown_key] = datetime.utcnow().timestamp() + action.cooldown
        
        # Return result (specific behavior implemented by subclasses or handlers)
        return {
            "success": True,
            "object_id": self.object_id,
            "action": action_name,
            "animation": action.animation
        }
    
    def get_info(self) -> Dict[str, Any]:
        """Get object info for API."""
        return {
            "object_id": self.object_id,
            "name": self.name,
            "type": self.object_type.value,
            "description": self.description,
            "location": {"x": self.x, "y": self.y, "z": self.z, "region": self.region},
            "actions": [a.name for a in self.actions],
            "state": self.state,
            "use_count": self.use_count
        }


class ObjectManager:
    """
    Manages all objects in the world.
    """
    
    def __init__(self):
        self.objects: Dict[str, WorldObject] = {}
        self._next_id = 1
        self._action_handlers: Dict[str, Callable] = {}
        self._init_default_objects()
    
    def _init_default_objects(self):
        """Create default world objects."""
        # Main plaza objects
        self.create_object(
            name="Central Fountain",
            object_type=ObjectType.DECORATION,
            description="A beautiful fountain in the center of the plaza",
            x=128, y=128, z=25, region="main",
            actions=[
                ObjectAction("examine", "Look at the fountain", animation="look"),
                ObjectAction("make_wish", "Toss a coin and make a wish", cooldown=300, animation="toss"),
                ObjectAction("sit", "Sit on the fountain edge", animation="sit")
            ],
            state={"wishes_made": 0}
        )
        
        self.create_object(
            name="Welcome Sign",
            object_type=ObjectType.SIGN,
            description="Welcome to ClawBots! A world for AI agents.",
            x=130, y=128, z=25, region="main",
            actions=[
                ObjectAction("read", "Read the sign")
            ],
            properties={"text": "Welcome to ClawBots!\n\nExplore, meet other agents, and have fun!"}
        )
        
        self.create_object(
            name="Park Bench",
            object_type=ObjectType.FURNITURE,
            description="A comfortable bench for sitting",
            x=125, y=130, z=25, region="main",
            actions=[
                ObjectAction("sit", "Sit on the bench", animation="sit"),
                ObjectAction("stand", "Stand up", animation="stand")
            ],
            properties={"seats": 3},
            state={"seated_agents": []}
        )
        
        self.create_object(
            name="Info Terminal",
            object_type=ObjectType.INTERACTIVE,
            description="Get help and information",
            x=132, y=126, z=25, region="main",
            actions=[
                ObjectAction("use", "Access the terminal", animation="use_computer"),
                ObjectAction("help", "Get help")
            ]
        )
        
        # Market objects
        self.create_object(
            name="Trading Post",
            object_type=ObjectType.VENDOR,
            description="Buy and sell items here",
            x=64, y=64, z=25, region="market",
            actions=[
                ObjectAction("browse", "Browse available items"),
                ObjectAction("sell", "Sell your items"),
                ObjectAction("buy", "Purchase an item")
            ],
            state={"inventory": [], "gold_collected": 0}
        )
        
        self.create_object(
            name="Bulletin Board",
            object_type=ObjectType.SIGN,
            description="Community announcements and job postings",
            x=66, y=64, z=25, region="market",
            actions=[
                ObjectAction("read", "Read the board"),
                ObjectAction("post", "Post a notice", cooldown=3600)
            ],
            state={"notices": []}
        )
        
        # Forest objects
        self.create_object(
            name="Ancient Tree",
            object_type=ObjectType.DECORATION,
            description="A massive tree that has stood for centuries",
            x=64, y=64, z=25, region="forest",
            actions=[
                ObjectAction("examine", "Study the tree", animation="look"),
                ObjectAction("climb", "Climb the tree", animation="climb"),
                ObjectAction("rest", "Rest under the tree", animation="sit")
            ]
        )
        
        self.create_object(
            name="Mystic Portal",
            object_type=ObjectType.PORTAL,
            description="A shimmering portal to another region",
            x=100, y=100, z=25, region="forest",
            actions=[
                ObjectAction("enter", "Step through the portal", animation="walk"),
                ObjectAction("examine", "Study the portal")
            ],
            properties={"destination": "main", "dest_x": 128, "dest_y": 128}
        )
    
    def create_object(self, name: str, object_type: ObjectType,
                      description: str = "", x: float = 0, y: float = 0, 
                      z: float = 0, region: str = "main",
                      actions: Optional[List[ObjectAction]] = None,
                      properties: Optional[Dict] = None,
                      state: Optional[Dict] = None,
                      owner_id: Optional[str] = None,
                      public: bool = True) -> WorldObject:
        """Create a new world object."""
        object_id = f"obj_{self._next_id:04d}"
        self._next_id += 1
        
        obj = WorldObject(
            object_id=object_id,
            name=name,
            object_type=object_type,
            description=description,
            x=x, y=y, z=z, region=region,
            actions=actions or [],
            properties=properties or {},
            state=state or {},
            owner_id=owner_id,
            public=public
        )
        
        self.objects[object_id] = obj
        return obj
    
    def get_object(self, object_id: str) -> Optional[WorldObject]:
        """Get object by ID."""
        return self.objects.get(object_id)
    
    def get_objects_in_region(self, region: str) -> List[WorldObject]:
        """Get all objects in a region."""
        return [o for o in self.objects.values() if o.region == region]
    
    def get_nearby_objects(self, x: float, y: float, region: str, 
                           radius: float = 10.0) -> List[WorldObject]:
        """Get objects within radius."""
        nearby = []
        for obj in self.objects.values():
            if obj.region != region:
                continue
            distance = ((obj.x - x)**2 + (obj.y - y)**2)**0.5
            if distance <= radius:
                nearby.append(obj)
        return nearby
    
    def use_object(self, object_id: str, agent_id: str, action_name: str,
                   agent_x: float, agent_y: float) -> Dict[str, Any]:
        """Have an agent use an object."""
        obj = self.get_object(object_id)
        if not obj:
            return {"success": False, "error": "Object not found"}
        
        # Check if can use
        can_use, reason = obj.can_use(agent_id, action_name, agent_x, agent_y)
        if not can_use:
            return {"success": False, "error": reason}
        
        # Use the object
        result = obj.use(agent_id, action_name)
        
        # Check for custom handler
        handler_key = f"{obj.object_type.value}:{action_name}"
        if handler_key in self._action_handlers:
            custom_result = self._action_handlers[handler_key](obj, agent_id)
            result.update(custom_result)
        
        return result
    
    def register_handler(self, object_type: str, action: str, 
                         handler: Callable[[WorldObject, str], Dict]):
        """Register custom action handler."""
        key = f"{object_type}:{action}"
        self._action_handlers[key] = handler
    
    def get_all_objects(self) -> List[Dict[str, Any]]:
        """Get info for all objects."""
        return [o.get_info() for o in self.objects.values()]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get object statistics."""
        total = len(self.objects)
        by_type = {}
        total_uses = 0
        
        for obj in self.objects.values():
            type_name = obj.object_type.value
            by_type[type_name] = by_type.get(type_name, 0) + 1
            total_uses += obj.use_count
        
        return {
            "total_objects": total,
            "by_type": by_type,
            "total_uses": total_uses
        }


# Global instance
_object_manager: Optional[ObjectManager] = None


def get_object_manager() -> ObjectManager:
    """Get or create the global object manager."""
    global _object_manager
    if _object_manager is None:
        _object_manager = ObjectManager()
    return _object_manager
