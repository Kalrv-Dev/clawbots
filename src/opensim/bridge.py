"""
ClawBots OpenSim Bridge

Connects ClawBots platform to OpenSim virtual world.
Translates between platform events and OpenSim protocol.
"""

from typing import Optional, Dict, List, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import asyncio
import aiohttp
import json


class OpenSimEventType(Enum):
    """Types of events from OpenSim."""
    AVATAR_ENTER = "avatar_enter"
    AVATAR_LEAVE = "avatar_leave"
    AVATAR_MOVE = "avatar_move"
    CHAT_MESSAGE = "chat_message"
    OBJECT_TOUCH = "object_touch"
    REGION_CHANGE = "region_change"


@dataclass
class OpenSimConfig:
    """Configuration for OpenSim connection."""
    grid_url: str = "http://localhost:9000"
    region_name: str = "ClawBots"
    admin_name: str = "ClawBots Admin"
    admin_password: str = ""
    
    # API endpoints
    rest_api_port: int = 9000
    xmlrpc_port: int = 9000
    
    # Connection settings
    reconnect_interval: float = 5.0
    heartbeat_interval: float = 30.0
    
    # Avatar settings
    default_avatar_type: str = "Ruth2"
    spawn_location: Dict[str, float] = field(
        default_factory=lambda: {"x": 128, "y": 128, "z": 25}
    )


@dataclass
class OpenSimEvent:
    """An event from OpenSim."""
    type: OpenSimEventType
    timestamp: datetime
    avatar_id: Optional[str] = None
    avatar_name: Optional[str] = None
    region: Optional[str] = None
    position: Optional[Dict[str, float]] = None
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OpenSimAvatar:
    """Represents an avatar in OpenSim."""
    uuid: str
    name: str
    agent_id: str  # ClawBots agent ID
    region: str
    position: Dict[str, float]
    rotation: float = 0.0
    is_bot: bool = True


class OpenSimBridge:
    """
    Bridge between ClawBots platform and OpenSim.
    
    Responsibilities:
    - Manage connection to OpenSim grid
    - Spawn/despawn bot avatars
    - Relay chat messages
    - Sync avatar positions
    - Translate events between systems
    """
    
    def __init__(self, config: OpenSimConfig, world_engine):
        self.config = config
        self.world = world_engine
        
        self.connected: bool = False
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Active avatars (agent_id -> OpenSimAvatar)
        self.avatars: Dict[str, OpenSimAvatar] = {}
        
        # Event handlers
        self.event_handlers: List[Callable] = []
        
        # Queue for outgoing commands
        self.command_queue: asyncio.Queue = asyncio.Queue()
        
    # ========== CONNECTION ==========
    
    async def connect(self) -> bool:
        """Connect to OpenSim grid."""
        try:
            self.session = aiohttp.ClientSession()
            
            # Test connection
            async with self.session.get(
                f"{self.config.grid_url}/simstatus/"
            ) as resp:
                if resp.status == 200:
                    self.connected = True
                    print(f"✅ Connected to OpenSim: {self.config.grid_url}")
                    
                    # Start background tasks
                    asyncio.create_task(self._heartbeat_loop())
                    asyncio.create_task(self._event_poll_loop())
                    asyncio.create_task(self._command_loop())
                    
                    return True
                    
        except Exception as e:
            print(f"❌ OpenSim connection failed: {e}")
            self.connected = False
            
        return False
    
    async def disconnect(self) -> None:
        """Disconnect from OpenSim."""
        self.connected = False
        
        # Despawn all avatars
        for agent_id in list(self.avatars.keys()):
            await self.despawn_avatar(agent_id)
        
        if self.session:
            await self.session.close()
            self.session = None
            
        print("🔌 Disconnected from OpenSim")
    
    async def _heartbeat_loop(self) -> None:
        """Send periodic heartbeats."""
        while self.connected:
            await asyncio.sleep(self.config.heartbeat_interval)
            try:
                async with self.session.get(
                    f"{self.config.grid_url}/simstatus/"
                ) as resp:
                    if resp.status != 200:
                        self.connected = False
            except:
                self.connected = False
    
    # ========== AVATAR MANAGEMENT ==========
    
    async def spawn_avatar(
        self,
        agent_id: str,
        name: str,
        region: Optional[str] = None,
        position: Optional[Dict[str, float]] = None,
        avatar_type: Optional[str] = None
    ) -> Optional[OpenSimAvatar]:
        """Spawn a bot avatar in OpenSim."""
        if not self.connected:
            return None
        
        region = region or self.config.region_name
        position = position or self.config.spawn_location.copy()
        avatar_type = avatar_type or self.config.default_avatar_type
        
        # Create avatar via OpenSim API
        try:
            payload = {
                "firstname": name.split()[0] if " " in name else name,
                "lastname": f"Bot_{agent_id[:8]}",
                "region": region,
                "position": position,
                "avatar_type": avatar_type
            }
            
            async with self.session.post(
                f"{self.config.grid_url}/admin/create_avatar",
                json=payload
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    avatar = OpenSimAvatar(
                        uuid=data.get("uuid", f"bot_{agent_id}"),
                        name=f"{payload['firstname']} {payload['lastname']}",
                        agent_id=agent_id,
                        region=region,
                        position=position
                    )
                    
                    self.avatars[agent_id] = avatar
                    print(f"🤖 Spawned avatar: {avatar.name}")
                    
                    return avatar
                    
        except Exception as e:
            print(f"❌ Avatar spawn failed: {e}")
            
            # Create mock avatar for testing
            avatar = OpenSimAvatar(
                uuid=f"mock_{agent_id}",
                name=f"{name} Bot",
                agent_id=agent_id,
                region=region,
                position=position
            )
            self.avatars[agent_id] = avatar
            return avatar
        
        return None
    
    async def despawn_avatar(self, agent_id: str) -> bool:
        """Remove a bot avatar from OpenSim."""
        if agent_id not in self.avatars:
            return False
        
        avatar = self.avatars[agent_id]
        
        try:
            async with self.session.post(
                f"{self.config.grid_url}/admin/remove_avatar",
                json={"uuid": avatar.uuid}
            ) as resp:
                pass  # Best effort
        except:
            pass
        
        del self.avatars[agent_id]
        print(f"👋 Despawned avatar: {avatar.name}")
        return True
    
    async def move_avatar(
        self,
        agent_id: str,
        position: Dict[str, float]
    ) -> bool:
        """Move an avatar to a new position."""
        if agent_id not in self.avatars:
            return False
        
        avatar = self.avatars[agent_id]
        
        # Queue movement command
        await self.command_queue.put({
            "type": "move",
            "uuid": avatar.uuid,
            "position": position
        })
        
        avatar.position = position
        return True
    
    async def avatar_say(
        self,
        agent_id: str,
        message: str,
        channel: int = 0
    ) -> bool:
        """Make an avatar say something."""
        if agent_id not in self.avatars:
            return False
        
        avatar = self.avatars[agent_id]
        
        # Queue chat command
        await self.command_queue.put({
            "type": "chat",
            "uuid": avatar.uuid,
            "message": message,
            "channel": channel
        })
        
        return True
    
    async def avatar_animate(
        self,
        agent_id: str,
        animation: str
    ) -> bool:
        """Play an animation on an avatar."""
        if agent_id not in self.avatars:
            return False
        
        avatar = self.avatars[agent_id]
        
        await self.command_queue.put({
            "type": "animate",
            "uuid": avatar.uuid,
            "animation": animation
        })
        
        return True
    
    # ========== EVENT HANDLING ==========
    
    async def _event_poll_loop(self) -> None:
        """Poll for events from OpenSim."""
        while self.connected:
            await asyncio.sleep(0.5)  # Poll interval
            
            try:
                async with self.session.get(
                    f"{self.config.grid_url}/events/poll"
                ) as resp:
                    if resp.status == 200:
                        events = await resp.json()
                        for event_data in events:
                            await self._handle_opensim_event(event_data)
            except:
                pass  # Ignore poll errors
    
    async def _handle_opensim_event(self, event_data: Dict[str, Any]) -> None:
        """Handle an event from OpenSim."""
        event_type = event_data.get("type", "")
        
        # Create OpenSimEvent
        event = OpenSimEvent(
            type=OpenSimEventType(event_type) if event_type in [e.value for e in OpenSimEventType] else OpenSimEventType.CHAT_MESSAGE,
            timestamp=datetime.utcnow(),
            avatar_id=event_data.get("avatar_id"),
            avatar_name=event_data.get("avatar_name"),
            region=event_data.get("region"),
            position=event_data.get("position"),
            data=event_data
        )
        
        # Call handlers
        for handler in self.event_handlers:
            try:
                await handler(event)
            except Exception as e:
                print(f"Event handler error: {e}")
        
        # Translate to ClawBots event
        await self._translate_to_clawbots(event)
    
    async def _translate_to_clawbots(self, event: OpenSimEvent) -> None:
        """Translate OpenSim event to ClawBots world event."""
        if event.type == OpenSimEventType.CHAT_MESSAGE:
            # Find if this is from a known avatar
            message = event.data.get("message", "")
            
            # Relay to world
            if hasattr(self.world, 'broadcast_speech'):
                # Find agent by avatar name
                for agent_id, avatar in self.avatars.items():
                    if avatar.uuid == event.avatar_id:
                        await self.world.broadcast_speech(
                            agent_id, message, "normal"
                        )
                        break
        
        elif event.type == OpenSimEventType.AVATAR_MOVE:
            if event.position and event.avatar_id:
                for agent_id, avatar in self.avatars.items():
                    if avatar.uuid == event.avatar_id:
                        await self.world.move_agent(
                            agent_id,
                            event.position.get("x", 128),
                            event.position.get("y", 128),
                            event.position.get("z", 25)
                        )
                        break
    
    def on_event(self, handler: Callable) -> None:
        """Register an event handler."""
        self.event_handlers.append(handler)
    
    # ========== COMMAND EXECUTION ==========
    
    async def _command_loop(self) -> None:
        """Process outgoing commands."""
        while self.connected:
            try:
                command = await asyncio.wait_for(
                    self.command_queue.get(),
                    timeout=1.0
                )
                await self._execute_command(command)
            except asyncio.TimeoutError:
                continue
    
    async def _execute_command(self, command: Dict[str, Any]) -> None:
        """Execute a command in OpenSim."""
        cmd_type = command.get("type")
        
        try:
            if cmd_type == "move":
                await self.session.post(
                    f"{self.config.grid_url}/avatar/move",
                    json={
                        "uuid": command["uuid"],
                        "position": command["position"]
                    }
                )
            
            elif cmd_type == "chat":
                await self.session.post(
                    f"{self.config.grid_url}/avatar/chat",
                    json={
                        "uuid": command["uuid"],
                        "message": command["message"],
                        "channel": command.get("channel", 0)
                    }
                )
            
            elif cmd_type == "animate":
                await self.session.post(
                    f"{self.config.grid_url}/avatar/animate",
                    json={
                        "uuid": command["uuid"],
                        "animation": command["animation"]
                    }
                )
        except Exception as e:
            print(f"Command execution error: {e}")
    
    # ========== WORLD INTEGRATION ==========
    
    async def sync_from_world(self, agent_id: str) -> None:
        """Sync ClawBots agent state to OpenSim."""
        agent = self.world.get_agent(agent_id)
        if not agent:
            return
        
        if agent_id not in self.avatars:
            # Spawn if not exists
            await self.spawn_avatar(
                agent_id,
                agent.name,
                agent.location.region if hasattr(agent.location, 'region') else None,
                {
                    "x": agent.location.x,
                    "y": agent.location.y,
                    "z": agent.location.z
                } if hasattr(agent, 'location') else None
            )
        else:
            # Update position
            if hasattr(agent, 'location'):
                await self.move_avatar(agent_id, {
                    "x": agent.location.x,
                    "y": agent.location.y,
                    "z": agent.location.z
                })
    
    async def relay_speech_to_opensim(
        self,
        agent_id: str,
        message: str
    ) -> None:
        """Relay a ClawBots speech event to OpenSim."""
        await self.avatar_say(agent_id, message)
    
    # ========== UTILITIES ==========
    
    def get_stats(self) -> Dict[str, Any]:
        """Get bridge statistics."""
        return {
            "connected": self.connected,
            "grid_url": self.config.grid_url,
            "region": self.config.region_name,
            "avatars": len(self.avatars),
            "avatar_list": [
                {
                    "agent_id": a.agent_id,
                    "name": a.name,
                    "region": a.region
                }
                for a in self.avatars.values()
            ]
        }
