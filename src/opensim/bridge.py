"""
ClawBots OpenSim Bridge

Full integration between ClawBots platform and OpenSim grid.
Manages bot avatars as real OpenSim avatars.
"""

from typing import Optional, Dict, List, Any, Callable
from dataclasses import dataclass
from datetime import datetime
import asyncio

from .config import OpenSimConfig, get_opensim_config
from .remote_admin import RemoteAdminClient, UserAccount
from .bot_controller import BotController, BotAvatar, BotState


@dataclass
class BotCredentials:
    """Stored credentials for a bot account."""
    agent_id: str
    first_name: str
    last_name: str
    password: str
    uuid: str = ""


class OpenSimBridge:
    """
    Bridge between ClawBots and OpenSim.
    
    When an agent connects to ClawBots:
    1. Creates OpenSim account (if needed)
    2. Logs in bot avatar
    3. Syncs position/chat/actions
    
    Humans can join via Firestorm and see all the bots!
    """
    
    def __init__(self, world_engine, config: Optional[OpenSimConfig] = None):
        self.config = config or get_opensim_config()
        self.world = world_engine
        
        # Components
        self.admin: Optional[RemoteAdminClient] = None
        self.controller: Optional[BotController] = None
        
        # Bot credentials storage
        self.credentials: Dict[str, BotCredentials] = {}
        
        # State
        self.connected = False
        self._running = False
        self._sync_task: Optional[asyncio.Task] = None
        
        # Callbacks
        self._on_ready: List[Callable] = []
    
    # ========== LIFECYCLE ==========
    
    async def connect(self) -> bool:
        """
        Connect to OpenSim grid.
        
        Initializes RemoteAdmin and BotController.
        """
        try:
            # Initialize RemoteAdmin
            self.admin = RemoteAdminClient(
                url=self.config.remote_admin_url,
                password=self.config.remote_admin_password
            )
            
            # Test connection
            if await self.admin.ping():
                print(f"✅ Connected to OpenSim RemoteAdmin: {self.config.remote_admin_url}")
            else:
                print(f"⚠️ RemoteAdmin not responding, continuing in mock mode")
            
            # Initialize BotController
            self.controller = BotController(
                grid_url=self.config.grid_url,
                login_uri=f"{self.config.grid_url}/"
            )
            await self.controller.start()
            
            self.connected = True
            self._running = True
            
            # Start sync loop
            self._sync_task = asyncio.create_task(self._sync_loop())
            
            # Notify ready callbacks
            for callback in self._on_ready:
                await callback()
            
            print(f"🌐 OpenSim Bridge connected to {self.config.grid_name}")
            return True
            
        except Exception as e:
            print(f"❌ OpenSim Bridge connection failed: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from OpenSim grid."""
        self._running = False
        
        if self._sync_task:
            self._sync_task.cancel()
        
        # Logout all bots
        if self.controller:
            await self.controller.stop()
        
        self.connected = False
        print("🔌 OpenSim Bridge disconnected")
    
    def on_ready(self, callback: Callable):
        """Register callback for when bridge is ready."""
        self._on_ready.append(callback)
    
    # ========== BOT MANAGEMENT ==========
    
    async def spawn_agent(
        self,
        agent_id: str,
        name: str,
        region: Optional[str] = None,
        position: Optional[Dict[str, float]] = None
    ) -> Optional[BotAvatar]:
        """
        Spawn a ClawBots agent as an OpenSim avatar.
        
        Creates account if needed, then logs in.
        """
        if not self.connected:
            return None
        
        # Determine names
        first_name = name.split()[0] if " " in name else name
        last_name = self.config.bot_last_name
        
        # Check if we have credentials
        if agent_id in self.credentials:
            creds = self.credentials[agent_id]
        else:
            # Create new bot account
            print(f"📝 Creating OpenSim account for {first_name} {last_name}...")
            
            account = await self.admin.create_bot_account(
                bot_name=first_name,
                bot_last_name=last_name,
                start_region=region or self.config.default_region
            )
            
            if account:
                creds = BotCredentials(
                    agent_id=agent_id,
                    first_name=account.first_name,
                    last_name=account.last_name,
                    password=getattr(account, 'password', 'botpass123'),
                    uuid=account.uuid
                )
                self.credentials[agent_id] = creds
            else:
                # Fallback credentials
                creds = BotCredentials(
                    agent_id=agent_id,
                    first_name=first_name,
                    last_name=last_name,
                    password="botpass123"
                )
                self.credentials[agent_id] = creds
        
        # Create bot in controller
        bot = await self.controller.create_bot(
            agent_id=agent_id,
            first_name=creds.first_name,
            last_name=creds.last_name,
            password=creds.password
        )
        
        # Login to grid
        spawn_region = region or self.config.default_region
        spawn_pos = position or self.config.spawn_location
        
        success = await self.controller.login_bot(
            agent_id=agent_id,
            region=spawn_region,
            position=spawn_pos
        )
        
        if success:
            print(f"🤖 Agent spawned in OpenSim: {creds.first_name} {creds.last_name}")
            return bot
        
        return None
    
    async def despawn_agent(self, agent_id: str) -> bool:
        """Remove an agent from OpenSim."""
        if not self.controller:
            return False
        
        return await self.controller.logout_bot(agent_id)
    
    async def get_bot(self, agent_id: str) -> Optional[BotAvatar]:
        """Get bot avatar for an agent."""
        if not self.controller:
            return None
        return self.controller.get_bot(agent_id)
    
    # ========== ACTIONS ==========
    
    async def move_agent(
        self,
        agent_id: str,
        x: float,
        y: float,
        z: Optional[float] = None
    ) -> bool:
        """Move an agent's avatar."""
        if not self.controller:
            return False
        return await self.controller.move_bot(agent_id, x, y, z)
    
    async def agent_say(
        self,
        agent_id: str,
        message: str,
        channel: int = 0
    ) -> bool:
        """Make an agent's avatar speak."""
        if not self.controller:
            return False
        return await self.controller.bot_say(agent_id, message, channel)
    
    async def agent_shout(self, agent_id: str, message: str) -> bool:
        """Make an agent's avatar shout."""
        if not self.controller:
            return False
        return await self.controller.bot_shout(agent_id, message)
    
    async def agent_animate(
        self,
        agent_id: str,
        animation: str,
        start: bool = True
    ) -> bool:
        """Play animation on agent's avatar."""
        if not self.controller:
            return False
        return await self.controller.bot_animate(agent_id, animation, start)
    
    async def agent_teleport(
        self,
        agent_id: str,
        region: str,
        x: float = 128.0,
        y: float = 128.0,
        z: float = 25.0
    ) -> bool:
        """Teleport an agent's avatar."""
        if not self.controller:
            return False
        return await self.controller.bot_teleport(agent_id, region, x, y, z)
    
    async def agent_sit(self, agent_id: str, target_uuid: str) -> bool:
        """Make agent sit on object."""
        if not self.controller:
            return False
        return await self.controller.bot_sit(agent_id, target_uuid)
    
    async def agent_stand(self, agent_id: str) -> bool:
        """Make agent stand up."""
        if not self.controller:
            return False
        return await self.controller.bot_stand(agent_id)
    
    # ========== WORLD SYNC ==========
    
    async def _sync_loop(self):
        """
        Background loop to sync ClawBots world with OpenSim.
        
        - Syncs positions from ClawBots → OpenSim
        - Relays chat from ClawBots → OpenSim
        """
        while self._running:
            await asyncio.sleep(0.5)  # Sync interval
            
            try:
                await self._sync_positions()
            except Exception as e:
                print(f"Sync error: {e}")
    
    async def _sync_positions(self):
        """Sync agent positions from ClawBots to OpenSim."""
        if not self.config.sync_positions:
            return
        
        if not self.world or not self.controller:
            return
        
        # Get all agents from world
        for agent_id, bot in self.controller.bots.items():
            if not bot.is_online:
                continue
            
            # Get ClawBots agent position
            agent = self.world.get_agent(agent_id)
            if not agent:
                continue
            
            # Check if position changed
            loc = agent.location
            if hasattr(loc, 'x'):
                dx = abs(bot.x - loc.x)
                dy = abs(bot.y - loc.y)
                
                # Only sync if moved significantly
                if dx > 1.0 or dy > 1.0:
                    await self.controller.move_bot(
                        agent_id,
                        loc.x,
                        loc.y,
                        loc.z if hasattr(loc, 'z') else None
                    )
    
    async def relay_speech(self, agent_id: str, message: str, volume: str = "normal"):
        """Relay speech from ClawBots to OpenSim."""
        if not self.config.sync_chat:
            return
        
        if volume == "shout":
            await self.agent_shout(agent_id, message)
        else:
            await self.agent_say(agent_id, message)
    
    async def relay_emote(self, agent_id: str, action: str):
        """Relay emote from ClawBots to OpenSim as animation."""
        if not self.config.sync_animations:
            return
        
        # Map emote names to OpenSim animations
        animation_map = {
            "wave": "wave",
            "nod": "nod",
            "laugh": "laugh",
            "dance": "dance1",
            "sit": "sit",
            "stand": "stand",
            "bow": "bow",
            "shrug": "shrug",
            "think": "think"
        }
        
        animation = animation_map.get(action.lower(), action)
        await self.agent_animate(agent_id, animation)
    
    # ========== ADMIN ==========
    
    async def broadcast(self, message: str) -> bool:
        """Broadcast message to all avatars in grid."""
        if not self.admin:
            return False
        return await self.admin.broadcast_message(message)
    
    async def get_grid_status(self) -> Dict[str, Any]:
        """Get OpenSim grid status."""
        if not self.admin:
            return {"online": False, "error": "Not connected"}
        return await self.admin.get_grid_status()
    
    async def list_regions(self) -> List[Dict[str, Any]]:
        """List all regions in grid."""
        if not self.admin:
            return []
        return await self.admin.list_regions()
    
    # ========== STATUS ==========
    
    def get_stats(self) -> Dict[str, Any]:
        """Get bridge statistics."""
        controller_stats = self.controller.get_stats() if self.controller else {}
        
        return {
            "connected": self.connected,
            "grid_name": self.config.grid_name,
            "grid_url": self.config.grid_url,
            "default_region": self.config.default_region,
            "sync_enabled": {
                "positions": self.config.sync_positions,
                "chat": self.config.sync_chat,
                "animations": self.config.sync_animations
            },
            "bots": controller_stats.get("bots", []),
            "total_bots": controller_stats.get("total_bots", 0),
            "online_bots": controller_stats.get("online_bots", 0)
        }


# Global bridge instance
_bridge: Optional[OpenSimBridge] = None


def get_opensim_bridge(world_engine=None) -> Optional[OpenSimBridge]:
    """Get the global OpenSim bridge."""
    global _bridge
    if _bridge is None and world_engine is not None:
        _bridge = OpenSimBridge(world_engine)
    return _bridge


async def init_opensim_bridge(world_engine) -> OpenSimBridge:
    """Initialize and connect the OpenSim bridge."""
    global _bridge
    _bridge = OpenSimBridge(world_engine)
    await _bridge.connect()
    return _bridge
