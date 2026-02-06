"""
ClawBots OpenSim Bot Controller

Controls bot avatars in OpenSim grid.
Handles login, movement, chat, and animations.
"""

from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import asyncio
import aiohttp
import hashlib
import json


class BotState(Enum):
    """Bot avatar states."""
    OFFLINE = "offline"
    LOGGING_IN = "logging_in"
    ONLINE = "online"
    MOVING = "moving"
    SITTING = "sitting"
    ERROR = "error"


@dataclass
class BotAvatar:
    """
    A bot avatar in OpenSim.
    """
    # Identity
    agent_id: str           # ClawBots agent ID
    first_name: str
    last_name: str
    uuid: str = ""          # OpenSim avatar UUID
    
    # Credentials
    password_hash: str = ""
    session_id: str = ""
    secure_session_id: str = ""
    
    # Location
    region: str = ""
    x: float = 128.0
    y: float = 128.0
    z: float = 25.0
    rotation: float = 0.0
    
    # State
    state: BotState = BotState.OFFLINE
    last_update: float = 0.0
    error_message: str = ""
    
    # Stats
    login_time: Optional[str] = None
    message_count: int = 0
    move_count: int = 0
    
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"
    
    @property
    def is_online(self) -> bool:
        return self.state in (BotState.ONLINE, BotState.MOVING, BotState.SITTING)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "name": self.full_name,
            "uuid": self.uuid,
            "region": self.region,
            "position": {"x": self.x, "y": self.y, "z": self.z},
            "state": self.state.value,
            "online": self.is_online,
            "login_time": self.login_time,
            "message_count": self.message_count,
            "move_count": self.move_count
        }


class BotController:
    """
    Controls bot avatars in OpenSim.
    
    Uses OpenSim's REST API and XML-RPC for control.
    For full avatar control, integrates with LibreMetaverse-style protocols.
    """
    
    def __init__(self, grid_url: str, login_uri: Optional[str] = None):
        self.grid_url = grid_url.rstrip('/')
        self.login_uri = login_uri or f"{self.grid_url}/"
        
        self.bots: Dict[str, BotAvatar] = {}
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Event callbacks
        self._on_chat: List[Callable] = []
        self._on_move: List[Callable] = []
        self._on_event: List[Callable] = []
        
        # Background tasks
        self._running = False
        self._update_task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start the bot controller."""
        self.session = aiohttp.ClientSession()
        self._running = True
        self._update_task = asyncio.create_task(self._update_loop())
        print("🤖 Bot Controller started")
    
    async def stop(self):
        """Stop the bot controller."""
        self._running = False
        
        # Logout all bots
        for agent_id in list(self.bots.keys()):
            await self.logout_bot(agent_id)
        
        if self._update_task:
            self._update_task.cancel()
        
        if self.session:
            await self.session.close()
        
        print("🤖 Bot Controller stopped")
    
    # ========== BOT LIFECYCLE ==========
    
    async def create_bot(
        self,
        agent_id: str,
        first_name: str,
        last_name: str,
        password: str
    ) -> BotAvatar:
        """
        Create a bot instance (doesn't login yet).
        """
        # Hash password for LLSD login
        password_hash = "$1$" + hashlib.md5(password.encode()).hexdigest()
        
        bot = BotAvatar(
            agent_id=agent_id,
            first_name=first_name,
            last_name=last_name,
            password_hash=password_hash
        )
        
        self.bots[agent_id] = bot
        return bot
    
    async def login_bot(
        self,
        agent_id: str,
        region: Optional[str] = None,
        position: Optional[Dict[str, float]] = None
    ) -> bool:
        """
        Login a bot to the grid.
        
        Uses LLSD login protocol.
        """
        bot = self.bots.get(agent_id)
        if not bot:
            return False
        
        bot.state = BotState.LOGGING_IN
        
        # Build login parameters (LLSD format)
        login_params = {
            "first": bot.first_name,
            "last": bot.last_name,
            "passwd": bot.password_hash,
            "start": "last",  # or "home" or "uri:region&x&y&z"
            "channel": "ClawBots",
            "version": "0.1.0",
            "platform": "Lin",  # Linux
            "mac": "00:00:00:00:00:00",
            "id0": "00000000-0000-0000-0000-000000000000",
            "agree_to_tos": True,
            "read_critical": True,
        }
        
        if region:
            pos = position or {"x": 128, "y": 128, "z": 25}
            login_params["start"] = f"uri:{region}&{int(pos['x'])}&{int(pos['y'])}&{int(pos['z'])}"
        
        try:
            # Try XML-RPC login
            async with self.session.post(
                f"{self.login_uri}",
                json={"method": "login_to_simulator", "params": [login_params]},
                headers={"Content-Type": "application/json"}
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    if data.get("login") == "true":
                        bot.uuid = data.get("agent_id", "")
                        bot.session_id = data.get("session_id", "")
                        bot.secure_session_id = data.get("secure_session_id", "")
                        bot.region = data.get("region_name", region or "Unknown")
                        bot.x = float(data.get("position_x", 128))
                        bot.y = float(data.get("position_y", 128))
                        bot.z = float(data.get("position_z", 25))
                        bot.state = BotState.ONLINE
                        bot.login_time = datetime.utcnow().isoformat()
                        
                        print(f"✅ Bot logged in: {bot.full_name} @ {bot.region}")
                        return True
                    else:
                        bot.state = BotState.ERROR
                        bot.error_message = data.get("message", "Login failed")
                        print(f"❌ Bot login failed: {bot.error_message}")
                        return False
                        
        except Exception as e:
            bot.state = BotState.ERROR
            bot.error_message = str(e)
            print(f"❌ Bot login error: {e}")
            
            # Fallback: Mock login for testing
            if "Connection" in str(e) or "refused" in str(e):
                print(f"⚠️ OpenSim not reachable, using mock mode for {bot.full_name}")
                bot.uuid = f"mock-{agent_id}"
                bot.region = region or "Bhairav"
                bot.state = BotState.ONLINE
                bot.login_time = datetime.utcnow().isoformat()
                return True
        
        return False
    
    async def logout_bot(self, agent_id: str) -> bool:
        """Logout a bot from the grid."""
        bot = self.bots.get(agent_id)
        if not bot or not bot.is_online:
            return False
        
        try:
            # Send logout request
            if bot.session_id and not bot.uuid.startswith("mock-"):
                async with self.session.post(
                    f"{self.grid_url}/agent/{bot.uuid}/logout",
                    json={"session_id": bot.session_id}
                ) as resp:
                    pass  # Best effort
        except:
            pass
        
        bot.state = BotState.OFFLINE
        bot.session_id = ""
        print(f"👋 Bot logged out: {bot.full_name}")
        return True
    
    # ========== BOT ACTIONS ==========
    
    async def move_bot(
        self,
        agent_id: str,
        x: float,
        y: float,
        z: Optional[float] = None
    ) -> bool:
        """Move a bot to a position."""
        bot = self.bots.get(agent_id)
        if not bot or not bot.is_online:
            return False
        
        target_z = z if z is not None else bot.z
        
        try:
            if not bot.uuid.startswith("mock-"):
                async with self.session.post(
                    f"{self.grid_url}/agent/{bot.uuid}/move",
                    json={
                        "session_id": bot.session_id,
                        "position": [x, y, target_z]
                    }
                ) as resp:
                    if resp.status != 200:
                        return False
        except:
            pass  # Continue with local update
        
        # Update local state
        bot.x = x
        bot.y = y
        bot.z = target_z
        bot.move_count += 1
        bot.state = BotState.MOVING
        
        return True
    
    async def bot_say(
        self,
        agent_id: str,
        message: str,
        channel: int = 0
    ) -> bool:
        """Make a bot say something in local chat."""
        bot = self.bots.get(agent_id)
        if not bot or not bot.is_online:
            return False
        
        try:
            if not bot.uuid.startswith("mock-"):
                async with self.session.post(
                    f"{self.grid_url}/agent/{bot.uuid}/chat",
                    json={
                        "session_id": bot.session_id,
                        "message": message,
                        "channel": channel,
                        "type": 1  # Normal chat
                    }
                ) as resp:
                    pass
        except:
            pass
        
        bot.message_count += 1
        print(f"💬 {bot.full_name}: {message}")
        return True
    
    async def bot_shout(self, agent_id: str, message: str) -> bool:
        """Make a bot shout (heard further away)."""
        bot = self.bots.get(agent_id)
        if not bot or not bot.is_online:
            return False
        
        try:
            if not bot.uuid.startswith("mock-"):
                async with self.session.post(
                    f"{self.grid_url}/agent/{bot.uuid}/chat",
                    json={
                        "session_id": bot.session_id,
                        "message": message,
                        "channel": 0,
                        "type": 2  # Shout
                    }
                ) as resp:
                    pass
        except:
            pass
        
        bot.message_count += 1
        return True
    
    async def bot_whisper(
        self,
        agent_id: str,
        target_uuid: str,
        message: str
    ) -> bool:
        """Send an instant message to another avatar."""
        bot = self.bots.get(agent_id)
        if not bot or not bot.is_online:
            return False
        
        try:
            if not bot.uuid.startswith("mock-"):
                async with self.session.post(
                    f"{self.grid_url}/agent/{bot.uuid}/im",
                    json={
                        "session_id": bot.session_id,
                        "target_id": target_uuid,
                        "message": message
                    }
                ) as resp:
                    pass
        except:
            pass
        
        bot.message_count += 1
        return True
    
    async def bot_animate(
        self,
        agent_id: str,
        animation: str,
        start: bool = True
    ) -> bool:
        """Play or stop an animation on a bot."""
        bot = self.bots.get(agent_id)
        if not bot or not bot.is_online:
            return False
        
        try:
            if not bot.uuid.startswith("mock-"):
                async with self.session.post(
                    f"{self.grid_url}/agent/{bot.uuid}/animate",
                    json={
                        "session_id": bot.session_id,
                        "animation": animation,
                        "start": start
                    }
                ) as resp:
                    pass
        except:
            pass
        
        return True
    
    async def bot_sit(self, agent_id: str, target_uuid: str) -> bool:
        """Make a bot sit on an object."""
        bot = self.bots.get(agent_id)
        if not bot or not bot.is_online:
            return False
        
        try:
            if not bot.uuid.startswith("mock-"):
                async with self.session.post(
                    f"{self.grid_url}/agent/{bot.uuid}/sit",
                    json={
                        "session_id": bot.session_id,
                        "target_id": target_uuid
                    }
                ) as resp:
                    if resp.status == 200:
                        bot.state = BotState.SITTING
                        return True
        except:
            pass
        
        bot.state = BotState.SITTING
        return True
    
    async def bot_stand(self, agent_id: str) -> bool:
        """Make a bot stand up."""
        bot = self.bots.get(agent_id)
        if not bot:
            return False
        
        try:
            if not bot.uuid.startswith("mock-"):
                async with self.session.post(
                    f"{self.grid_url}/agent/{bot.uuid}/stand",
                    json={"session_id": bot.session_id}
                ) as resp:
                    pass
        except:
            pass
        
        bot.state = BotState.ONLINE
        return True
    
    async def bot_teleport(
        self,
        agent_id: str,
        region: str,
        x: float = 128.0,
        y: float = 128.0,
        z: float = 25.0
    ) -> bool:
        """Teleport a bot to another region."""
        bot = self.bots.get(agent_id)
        if not bot or not bot.is_online:
            return False
        
        try:
            if not bot.uuid.startswith("mock-"):
                async with self.session.post(
                    f"{self.grid_url}/agent/{bot.uuid}/teleport",
                    json={
                        "session_id": bot.session_id,
                        "region": region,
                        "position": [x, y, z]
                    }
                ) as resp:
                    if resp.status == 200:
                        bot.region = region
                        bot.x, bot.y, bot.z = x, y, z
                        return True
        except:
            pass
        
        # Local update for mock
        bot.region = region
        bot.x, bot.y, bot.z = x, y, z
        return True
    
    # ========== EVENT HANDLING ==========
    
    def on_chat(self, callback: Callable):
        """Register chat event callback."""
        self._on_chat.append(callback)
    
    def on_move(self, callback: Callable):
        """Register movement event callback."""
        self._on_move.append(callback)
    
    def on_event(self, callback: Callable):
        """Register general event callback."""
        self._on_event.append(callback)
    
    async def _update_loop(self):
        """Background loop for updates and events."""
        while self._running:
            await asyncio.sleep(1.0)
            
            for bot in self.bots.values():
                if bot.is_online:
                    bot.last_update = datetime.utcnow().timestamp()
                    
                    # If was moving, set back to online
                    if bot.state == BotState.MOVING:
                        bot.state = BotState.ONLINE
    
    # ========== UTILITIES ==========
    
    def get_bot(self, agent_id: str) -> Optional[BotAvatar]:
        """Get a bot by agent ID."""
        return self.bots.get(agent_id)
    
    def get_all_bots(self) -> List[BotAvatar]:
        """Get all bots."""
        return list(self.bots.values())
    
    def get_online_bots(self) -> List[BotAvatar]:
        """Get all online bots."""
        return [b for b in self.bots.values() if b.is_online]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get controller statistics."""
        bots = self.get_all_bots()
        online = self.get_online_bots()
        
        return {
            "total_bots": len(bots),
            "online_bots": len(online),
            "total_messages": sum(b.message_count for b in bots),
            "total_moves": sum(b.move_count for b in bots),
            "bots": [b.to_dict() for b in bots]
        }
