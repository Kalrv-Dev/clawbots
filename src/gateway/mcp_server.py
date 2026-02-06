"""
ClawBots MCP Server

Exposes world interaction tools via Model Context Protocol.
Any AI agent with MCP support can connect and interact.
"""

from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum
import asyncio
import json


class ToolCategory(Enum):
    PERCEPTION = "perception"
    COMMUNICATION = "communication"
    MOVEMENT = "movement"
    ACTION = "action"
    SYSTEM = "system"


@dataclass
class Location:
    x: float
    y: float
    z: float
    region: str = "main"


@dataclass
class AgentInfo:
    id: str
    name: str
    location: Location
    status: str = "idle"
    avatar_type: str = "humanoid"


@dataclass
class WorldEvent:
    type: str
    source: str
    content: Dict[str, Any]
    location: Optional[Location] = None
    timestamp: float = 0.0


class MCPServer:
    """
    MCP Server for ClawBots Platform.
    
    Exposes tools that agents can call to interact with the world:
    - Perception: See what's around
    - Communication: Talk to others
    - Movement: Navigate the world
    - Actions: Interact with objects/agents
    """
    
    def __init__(self, world_engine, auth, registry):
        self.world = world_engine
        self.auth = auth
        self.registry = registry
        self.connected_agents: Dict[str, "AgentSession"] = {}
        
    # ========== PERCEPTION TOOLS ==========
    
    async def get_location(self, agent_id: str) -> Location:
        """Get agent's current location in the world."""
        agent = self.world.get_agent(agent_id)
        return agent.location if agent else None
    
    async def get_nearby_agents(
        self, 
        agent_id: str, 
        radius: float = 10.0
    ) -> List[AgentInfo]:
        """Get list of agents within radius of calling agent."""
        return self.world.get_nearby_agents(agent_id, radius)
    
    async def get_nearby_objects(
        self,
        agent_id: str,
        radius: float = 10.0
    ) -> List[Dict[str, Any]]:
        """Get list of objects within radius."""
        return self.world.get_nearby_objects(agent_id, radius)
    
    async def get_region_info(self, agent_id: str) -> Dict[str, Any]:
        """Get information about current region."""
        agent = self.world.get_agent(agent_id)
        if not agent:
            return None
        return self.world.get_region_info(agent.location.region)
    
    async def observe_events(
        self,
        agent_id: str,
        event_types: Optional[List[str]] = None,
        since_timestamp: float = 0.0
    ) -> List[WorldEvent]:
        """Get recent events visible to this agent."""
        return self.world.get_events_for_agent(
            agent_id, 
            event_types, 
            since_timestamp
        )
    
    # ========== COMMUNICATION TOOLS ==========
    
    async def say(
        self,
        agent_id: str,
        message: str,
        volume: str = "normal"  # whisper, normal, shout
    ) -> bool:
        """
        Speak a message. Heard by nearby agents based on volume:
        - whisper: 2m radius
        - normal: 10m radius  
        - shout: entire region
        """
        return await self.world.broadcast_speech(
            agent_id, message, volume
        )
    
    async def whisper(
        self,
        agent_id: str,
        target_id: str,
        message: str
    ) -> bool:
        """Send private message to specific agent."""
        return await self.world.send_private_message(
            agent_id, target_id, message
        )
    
    async def emote(
        self,
        agent_id: str,
        action: str
    ) -> bool:
        """
        Perform an emote/gesture visible to nearby agents.
        Examples: wave, nod, shrug, laugh, think
        """
        return await self.world.perform_emote(agent_id, action)
    
    # ========== MOVEMENT TOOLS ==========
    
    async def move_to(
        self,
        agent_id: str,
        x: float,
        y: float,
        z: Optional[float] = None
    ) -> bool:
        """Walk to a location. Returns when arrived or blocked."""
        return await self.world.move_agent(agent_id, x, y, z)
    
    async def teleport(
        self,
        agent_id: str,
        region: str,
        x: float = 128.0,
        y: float = 128.0,
        z: float = 25.0
    ) -> bool:
        """Teleport to another region. Requires permission."""
        if not self.auth.can_access_region(agent_id, region):
            return False
        return await self.world.teleport_agent(agent_id, region, x, y, z)
    
    async def follow(
        self,
        agent_id: str,
        target_id: str,
        distance: float = 2.0
    ) -> bool:
        """Follow another agent at specified distance."""
        return await self.world.set_follow(agent_id, target_id, distance)
    
    async def stop(self, agent_id: str) -> bool:
        """Stop current movement/following."""
        return await self.world.stop_agent(agent_id)
    
    # ========== ACTION TOOLS ==========
    
    async def use_object(
        self,
        agent_id: str,
        object_id: str,
        action: str = "use"
    ) -> Dict[str, Any]:
        """Interact with a world object (sit, open, activate, etc)."""
        return await self.world.interact_with_object(
            agent_id, object_id, action
        )
    
    async def give_item(
        self,
        agent_id: str,
        target_id: str,
        item_id: str
    ) -> bool:
        """Give an inventory item to another agent."""
        return await self.world.transfer_item(
            agent_id, target_id, item_id
        )
    
    async def set_status(
        self,
        agent_id: str,
        status: str,
        mood: Optional[str] = None
    ) -> bool:
        """Set visible status/mood (busy, available, away, etc)."""
        return await self.world.set_agent_status(agent_id, status, mood)
    
    # ========== SYSTEM TOOLS ==========
    
    async def get_time(self) -> Dict[str, Any]:
        """Get current world time and day/night cycle info."""
        return self.world.get_world_time()
    
    async def get_weather(self, region: Optional[str] = None) -> Dict[str, Any]:
        """Get current weather in region."""
        return self.world.get_weather(region)
    
    async def ping(self) -> Dict[str, Any]:
        """Health check - returns server status."""
        return {
            "status": "ok",
            "connected_agents": len(self.connected_agents),
            "world_tick": self.world.current_tick
        }
    
    # ========== CONNECTION MANAGEMENT ==========
    
    async def connect(
        self,
        agent_id: str,
        token: str,
        spawn_region: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Connect agent to the world.
        Returns spawn location and initial state.
        """
        # Verify token
        if not self.auth.verify_token(agent_id, token):
            return {"error": "Invalid token"}
        
        # Get agent config
        config = self.registry.get_agent_config(agent_id)
        
        # Spawn in world
        location = await self.world.spawn_agent(
            agent_id,
            config,
            spawn_region or config.get("default_region", "main")
        )
        
        # Track session
        self.connected_agents[agent_id] = AgentSession(
            agent_id=agent_id,
            connected_at=asyncio.get_event_loop().time()
        )
        
        return {
            "status": "connected",
            "location": location,
            "config": config
        }
    
    async def disconnect(self, agent_id: str) -> bool:
        """Disconnect agent from world."""
        if agent_id in self.connected_agents:
            await self.world.despawn_agent(agent_id)
            del self.connected_agents[agent_id]
            return True
        return False
    
    # ========== TOOL REGISTRY ==========
    
    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Return MCP-compatible tool definitions."""
        return [
            # Perception
            {
                "name": "get_location",
                "description": "Get your current location in the world",
                "category": "perception",
                "parameters": {}
            },
            {
                "name": "get_nearby_agents",
                "description": "Get list of agents near you",
                "category": "perception",
                "parameters": {
                    "radius": {"type": "number", "default": 10.0}
                }
            },
            {
                "name": "get_nearby_objects",
                "description": "Get list of objects near you",
                "category": "perception",
                "parameters": {
                    "radius": {"type": "number", "default": 10.0}
                }
            },
            {
                "name": "observe_events",
                "description": "Get recent events you can see/hear",
                "category": "perception",
                "parameters": {
                    "event_types": {"type": "array", "items": "string"},
                    "since_timestamp": {"type": "number", "default": 0}
                }
            },
            # Communication
            {
                "name": "say",
                "description": "Speak to nearby agents",
                "category": "communication",
                "parameters": {
                    "message": {"type": "string", "required": True},
                    "volume": {"type": "string", "enum": ["whisper", "normal", "shout"]}
                }
            },
            {
                "name": "whisper",
                "description": "Send private message to specific agent",
                "category": "communication",
                "parameters": {
                    "target_id": {"type": "string", "required": True},
                    "message": {"type": "string", "required": True}
                }
            },
            {
                "name": "emote",
                "description": "Perform a gesture/emote",
                "category": "communication",
                "parameters": {
                    "action": {"type": "string", "required": True}
                }
            },
            # Movement
            {
                "name": "move_to",
                "description": "Walk to a location",
                "category": "movement",
                "parameters": {
                    "x": {"type": "number", "required": True},
                    "y": {"type": "number", "required": True},
                    "z": {"type": "number"}
                }
            },
            {
                "name": "teleport",
                "description": "Teleport to another region",
                "category": "movement",
                "parameters": {
                    "region": {"type": "string", "required": True},
                    "x": {"type": "number", "default": 128},
                    "y": {"type": "number", "default": 128},
                    "z": {"type": "number", "default": 25}
                }
            },
            {
                "name": "follow",
                "description": "Follow another agent",
                "category": "movement",
                "parameters": {
                    "target_id": {"type": "string", "required": True},
                    "distance": {"type": "number", "default": 2.0}
                }
            },
            # Actions
            {
                "name": "use_object",
                "description": "Interact with a world object",
                "category": "action",
                "parameters": {
                    "object_id": {"type": "string", "required": True},
                    "action": {"type": "string", "default": "use"}
                }
            },
            {
                "name": "set_status",
                "description": "Set your visible status",
                "category": "action",
                "parameters": {
                    "status": {"type": "string", "required": True},
                    "mood": {"type": "string"}
                }
            }
        ]


@dataclass
class AgentSession:
    """Tracks a connected agent's session."""
    agent_id: str
    connected_at: float
    last_action: float = 0.0
    action_count: int = 0
