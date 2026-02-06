"""
ClawBots World Engine

The main simulation loop that ties everything together.
"""

from typing import Optional, Dict, List, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
import asyncio
import math


@dataclass
class Location:
    """3D location in the world."""
    x: float
    y: float
    z: float
    region: str = "main"
    
    def distance_to(self, other: "Location") -> float:
        """Calculate distance to another location."""
        if self.region != other.region:
            return float('inf')  # Different regions = infinite distance
        return math.sqrt(
            (self.x - other.x) ** 2 +
            (self.y - other.y) ** 2 +
            (self.z - other.z) ** 2
        )


@dataclass
class WorldAgent:
    """An agent instance in the world."""
    agent_id: str
    name: str
    location: Location
    avatar_config: Dict[str, Any]
    status: str = "idle"
    mood: str = "neutral"
    following: Optional[str] = None  # agent_id being followed
    last_action: float = 0.0


@dataclass
class WorldObject:
    """An interactive object in the world."""
    object_id: str
    name: str
    location: Location
    object_type: str
    properties: Dict[str, Any] = field(default_factory=dict)
    actions: List[str] = field(default_factory=lambda: ["use"])


@dataclass
class Region:
    """A region/zone in the world."""
    name: str
    display_name: str
    size: tuple = (256, 256)  # x, y dimensions
    spawn_point: Location = None
    properties: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if self.spawn_point is None:
            self.spawn_point = Location(128, 128, 25, self.name)


class WorldEngine:
    """
    Core world simulation engine.
    
    Manages:
    - Agents in the world (spawn, despawn, location)
    - Regions and spatial awareness
    - Events and broadcasting
    - Actions and interactions
    - World time and physics
    """
    
    def __init__(self):
        self.agents: Dict[str, WorldAgent] = {}
        self.objects: Dict[str, WorldObject] = {}
        self.regions: Dict[str, Region] = {}
        
        self.current_tick: int = 0
        self.tick_rate: float = 1.0  # seconds per tick
        self.running: bool = False
        
        self.event_handlers: List[Callable] = []
        self.event_history: List[Dict[str, Any]] = []
        
        # Initialize default region
        self._init_default_regions()
    
    def _init_default_regions(self):
        """Set up default regions."""
        self.regions["main"] = Region(
            name="main",
            display_name="Main Plaza",
            properties={"type": "public", "pvp": False}
        )
        self.regions["sandbox"] = Region(
            name="sandbox",
            display_name="Sandbox",
            properties={"type": "public", "building": True}
        )
    
    # ========== WORLD LOOP ==========
    
    async def run(self):
        """Main world simulation loop."""
        self.running = True
        while self.running:
            await self.tick()
            await asyncio.sleep(self.tick_rate)
    
    async def tick(self):
        """Process one world tick."""
        self.current_tick += 1
        
        # Update following agents
        await self._update_following()
        
        # Broadcast tick event
        await self._emit_event({
            "type": "world_tick",
            "tick": self.current_tick,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    def stop(self):
        """Stop the world loop."""
        self.running = False
    
    # ========== AGENT MANAGEMENT ==========
    
    async def spawn_agent(
        self,
        agent_id: str,
        config: Dict[str, Any],
        region: str = "main"
    ) -> Location:
        """Spawn an agent in the world."""
        if region not in self.regions:
            region = "main"
        
        spawn = self.regions[region].spawn_point
        location = Location(
            x=spawn.x + (hash(agent_id) % 10 - 5),  # Slight offset
            y=spawn.y + (hash(agent_id) % 10 - 5),
            z=spawn.z,
            region=region
        )
        
        self.agents[agent_id] = WorldAgent(
            agent_id=agent_id,
            name=config.get("name", agent_id),
            location=location,
            avatar_config=config.get("avatar", {})
        )
        
        await self._emit_event({
            "type": "agent_spawn",
            "agent_id": agent_id,
            "name": config.get("name", agent_id),
            "location": self._location_to_dict(location)
        })
        
        return location
    
    async def despawn_agent(self, agent_id: str) -> bool:
        """Remove an agent from the world."""
        if agent_id not in self.agents:
            return False
        
        agent = self.agents[agent_id]
        await self._emit_event({
            "type": "agent_despawn",
            "agent_id": agent_id,
            "location": self._location_to_dict(agent.location)
        })
        
        del self.agents[agent_id]
        return True
    
    def get_agent(self, agent_id: str) -> Optional[WorldAgent]:
        """Get an agent by ID."""
        return self.agents.get(agent_id)
    
    # ========== SPATIAL QUERIES ==========
    
    def get_nearby_agents(
        self,
        agent_id: str,
        radius: float = 10.0
    ) -> List[Dict[str, Any]]:
        """Get agents near a specific agent."""
        if agent_id not in self.agents:
            return []
        
        agent = self.agents[agent_id]
        nearby = []
        
        for other_id, other in self.agents.items():
            if other_id == agent_id:
                continue
            
            distance = agent.location.distance_to(other.location)
            if distance <= radius:
                nearby.append({
                    "agent_id": other_id,
                    "name": other.name,
                    "distance": round(distance, 2),
                    "status": other.status,
                    "mood": other.mood
                })
        
        return sorted(nearby, key=lambda x: x["distance"])
    
    def get_nearby_objects(
        self,
        agent_id: str,
        radius: float = 10.0
    ) -> List[Dict[str, Any]]:
        """Get objects near an agent."""
        if agent_id not in self.agents:
            return []
        
        agent = self.agents[agent_id]
        nearby = []
        
        for obj_id, obj in self.objects.items():
            distance = agent.location.distance_to(obj.location)
            if distance <= radius:
                nearby.append({
                    "object_id": obj_id,
                    "name": obj.name,
                    "type": obj.object_type,
                    "distance": round(distance, 2),
                    "actions": obj.actions
                })
        
        return sorted(nearby, key=lambda x: x["distance"])
    
    def get_region_info(self, region_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a region."""
        if region_name not in self.regions:
            return None
        
        region = self.regions[region_name]
        agents_in_region = [
            a.agent_id for a in self.agents.values()
            if a.location.region == region_name
        ]
        
        return {
            "name": region.name,
            "display_name": region.display_name,
            "size": region.size,
            "agents_count": len(agents_in_region),
            "properties": region.properties
        }
    
    # ========== COMMUNICATION ==========
    
    async def broadcast_speech(
        self,
        agent_id: str,
        message: str,
        volume: str = "normal"
    ) -> bool:
        """Broadcast speech from an agent."""
        if agent_id not in self.agents:
            return False
        
        agent = self.agents[agent_id]
        
        # Determine radius based on volume
        radius_map = {
            "whisper": 2.0,
            "normal": 10.0,
            "shout": float('inf')  # Entire region
        }
        radius = radius_map.get(volume, 10.0)
        
        await self._emit_event({
            "type": "speech",
            "agent_id": agent_id,
            "name": agent.name,
            "message": message,
            "volume": volume,
            "location": self._location_to_dict(agent.location),
            "radius": radius
        })
        
        return True
    
    async def send_private_message(
        self,
        from_id: str,
        to_id: str,
        message: str
    ) -> bool:
        """Send a private message between agents."""
        if from_id not in self.agents or to_id not in self.agents:
            return False
        
        await self._emit_event({
            "type": "private_message",
            "from_id": from_id,
            "to_id": to_id,
            "message": message,
            "private": True
        })
        
        return True
    
    async def perform_emote(self, agent_id: str, action: str) -> bool:
        """Perform an emote/gesture."""
        if agent_id not in self.agents:
            return False
        
        agent = self.agents[agent_id]
        
        await self._emit_event({
            "type": "emote",
            "agent_id": agent_id,
            "name": agent.name,
            "action": action,
            "location": self._location_to_dict(agent.location)
        })
        
        return True
    
    # ========== MOVEMENT ==========
    
    async def move_agent(
        self,
        agent_id: str,
        x: float,
        y: float,
        z: Optional[float] = None
    ) -> bool:
        """Move an agent to a location."""
        if agent_id not in self.agents:
            return False
        
        agent = self.agents[agent_id]
        old_location = agent.location
        
        # Update location
        agent.location = Location(
            x=x,
            y=y,
            z=z if z is not None else old_location.z,
            region=old_location.region
        )
        
        await self._emit_event({
            "type": "movement",
            "agent_id": agent_id,
            "from": self._location_to_dict(old_location),
            "to": self._location_to_dict(agent.location)
        })
        
        return True
    
    async def teleport_agent(
        self,
        agent_id: str,
        region: str,
        x: float,
        y: float,
        z: float
    ) -> bool:
        """Teleport an agent to another region."""
        if agent_id not in self.agents:
            return False
        if region not in self.regions:
            return False
        
        agent = self.agents[agent_id]
        old_location = agent.location
        
        agent.location = Location(x=x, y=y, z=z, region=region)
        
        await self._emit_event({
            "type": "teleport",
            "agent_id": agent_id,
            "from_region": old_location.region,
            "to_region": region,
            "location": self._location_to_dict(agent.location)
        })
        
        return True
    
    async def set_follow(
        self,
        agent_id: str,
        target_id: str,
        distance: float
    ) -> bool:
        """Set an agent to follow another."""
        if agent_id not in self.agents or target_id not in self.agents:
            return False
        
        self.agents[agent_id].following = target_id
        return True
    
    async def stop_agent(self, agent_id: str) -> bool:
        """Stop agent movement/following."""
        if agent_id not in self.agents:
            return False
        
        self.agents[agent_id].following = None
        return True
    
    async def _update_following(self):
        """Update positions of following agents."""
        for agent in self.agents.values():
            if agent.following and agent.following in self.agents:
                target = self.agents[agent.following]
                # Move towards target (simple following)
                distance = agent.location.distance_to(target.location)
                if distance > 2.0:  # Only move if far enough
                    # Move closer (simplified)
                    dx = target.location.x - agent.location.x
                    dy = target.location.y - agent.location.y
                    factor = 0.5  # Movement speed
                    agent.location.x += dx * factor
                    agent.location.y += dy * factor
    
    # ========== ACTIONS ==========
    
    async def interact_with_object(
        self,
        agent_id: str,
        object_id: str,
        action: str
    ) -> Dict[str, Any]:
        """Interact with a world object."""
        if agent_id not in self.agents:
            return {"error": "Agent not found"}
        if object_id not in self.objects:
            return {"error": "Object not found"}
        
        obj = self.objects[object_id]
        if action not in obj.actions:
            return {"error": f"Action '{action}' not available"}
        
        await self._emit_event({
            "type": "object_interaction",
            "agent_id": agent_id,
            "object_id": object_id,
            "action": action
        })
        
        return {"success": True, "action": action, "object": obj.name}
    
    async def set_agent_status(
        self,
        agent_id: str,
        status: str,
        mood: Optional[str] = None
    ) -> bool:
        """Set agent's visible status."""
        if agent_id not in self.agents:
            return False
        
        agent = self.agents[agent_id]
        agent.status = status
        if mood:
            agent.mood = mood
        
        await self._emit_event({
            "type": "status_change",
            "agent_id": agent_id,
            "status": status,
            "mood": mood
        })
        
        return True
    
    # ========== EVENTS ==========
    
    async def _emit_event(self, event: Dict[str, Any]):
        """Emit an event to all handlers."""
        event["timestamp"] = datetime.utcnow().isoformat()
        event["tick"] = self.current_tick
        
        self.event_history.append(event)
        
        # Keep history bounded
        if len(self.event_history) > 1000:
            self.event_history = self.event_history[-500:]
        
        # Call handlers
        for handler in self.event_handlers:
            try:
                await handler(event)
            except Exception as e:
                print(f"Event handler error: {e}")
    
    def on_event(self, handler: Callable):
        """Register an event handler."""
        self.event_handlers.append(handler)
    
    def get_events_for_agent(
        self,
        agent_id: str,
        event_types: Optional[List[str]] = None,
        since_timestamp: float = 0.0
    ) -> List[Dict[str, Any]]:
        """Get events visible to an agent."""
        if agent_id not in self.agents:
            return []
        
        agent = self.agents[agent_id]
        visible_events = []
        
        for event in self.event_history:
            # Filter by type
            if event_types and event.get("type") not in event_types:
                continue
            
            # Filter private messages
            if event.get("private"):
                if event.get("to_id") != agent_id and event.get("from_id") != agent_id:
                    continue
            
            # Filter by location (for spatial events)
            if "location" in event:
                event_loc = Location(**event["location"])
                if agent.location.distance_to(event_loc) > 50:
                    continue
            
            visible_events.append(event)
        
        return visible_events
    
    # ========== WORLD INFO ==========
    
    def get_world_time(self) -> Dict[str, Any]:
        """Get current world time."""
        # Simple day/night cycle based on real time
        hour = datetime.utcnow().hour
        is_day = 6 <= hour < 18
        
        return {
            "tick": self.current_tick,
            "real_time": datetime.utcnow().isoformat(),
            "is_day": is_day,
            "time_of_day": "day" if is_day else "night"
        }
    
    def get_weather(self, region: Optional[str] = None) -> Dict[str, Any]:
        """Get current weather (placeholder)."""
        return {
            "condition": "clear",
            "temperature": 22,
            "wind": "light",
            "region": region or "all"
        }
    
    # ========== UTILITIES ==========
    
    def _location_to_dict(self, loc: Location) -> Dict[str, Any]:
        """Convert Location to dictionary."""
        return {
            "x": loc.x,
            "y": loc.y,
            "z": loc.z,
            "region": loc.region
        }
