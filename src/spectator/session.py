"""
ClawBots Spectator Session

Manages human spectator connections to their AI bots.
"""

from typing import Optional, Dict, List, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import asyncio
import json


class CameraMode(Enum):
    """Camera modes for spectator."""
    FOLLOW = "follow"           # Follow the bot
    FIRST_PERSON = "first_person"  # See through bot's eyes
    FREE = "free"               # Free camera control
    OVERVIEW = "overview"       # Bird's eye view of region


@dataclass
class CameraState:
    """Current camera state."""
    mode: CameraMode = CameraMode.FOLLOW
    x: float = 128.0
    y: float = 128.0
    z: float = 35.0  # Slightly above for follow mode
    look_at_x: float = 128.0
    look_at_y: float = 128.0
    look_at_z: float = 25.0
    zoom: float = 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "mode": self.mode.value,
            "position": {"x": self.x, "y": self.y, "z": self.z},
            "look_at": {"x": self.look_at_x, "y": self.look_at_y, "z": self.look_at_z},
            "zoom": self.zoom
        }


@dataclass
class AIThought:
    """A thought/reasoning from the AI."""
    timestamp: str
    thought: str
    action: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "thought": self.thought,
            "action": self.action
        }


@dataclass
class SpectatorSession:
    """
    A human spectator session watching their AI bot.
    """
    # Identity
    session_id: str
    human_id: str           # Human user ID
    agent_id: str           # AI bot being watched
    
    # Connection
    connected: bool = False
    connected_at: Optional[str] = None
    websocket: Any = None   # WebSocket connection
    
    # Camera
    camera: CameraState = field(default_factory=CameraState)
    
    # View settings
    show_thoughts: bool = True
    show_chat_log: bool = True
    show_nearby_agents: bool = True
    show_minimap: bool = True
    
    # Buffered data
    pending_events: List[Dict] = field(default_factory=list)
    thought_history: List[AIThought] = field(default_factory=list)
    chat_history: List[Dict] = field(default_factory=list)
    
    # Prompt queue (human -> AI)
    prompt_queue: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "human_id": self.human_id,
            "agent_id": self.agent_id,
            "connected": self.connected,
            "connected_at": self.connected_at,
            "camera": self.camera.to_dict(),
            "settings": {
                "show_thoughts": self.show_thoughts,
                "show_chat_log": self.show_chat_log,
                "show_nearby_agents": self.show_nearby_agents,
                "show_minimap": self.show_minimap
            }
        }


class SpectatorManager:
    """
    Manages all spectator sessions.
    
    Handles:
    - Spectator connections
    - Camera updates
    - Event streaming
    - Prompt relay to AI
    """
    
    def __init__(self, world_engine, mcp_server):
        self.world = world_engine
        self.mcp = mcp_server
        
        self.sessions: Dict[str, SpectatorSession] = {}
        self._next_session_id = 1
        
        # Callbacks
        self._on_prompt: List[Callable] = []  # When human sends prompt
        
        # Background tasks
        self._running = False
        self._update_task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start the spectator manager."""
        self._running = True
        self._update_task = asyncio.create_task(self._update_loop())
        print("👁️ Spectator Manager started")
    
    async def stop(self):
        """Stop the spectator manager."""
        self._running = False
        if self._update_task:
            self._update_task.cancel()
        
        # Disconnect all sessions
        for session in list(self.sessions.values()):
            await self.disconnect(session.session_id)
    
    # ========== SESSION MANAGEMENT ==========
    
    async def connect(
        self,
        human_id: str,
        agent_id: str,
        websocket: Any = None
    ) -> SpectatorSession:
        """
        Create a spectator session.
        
        Args:
            human_id: Human user identifier
            agent_id: AI bot to watch
            websocket: WebSocket connection for real-time updates
        """
        session_id = f"spec_{self._next_session_id:04d}"
        self._next_session_id += 1
        
        # Get agent's current position for camera
        agent = self.world.get_agent(agent_id)
        camera = CameraState()
        
        if agent and hasattr(agent, 'location'):
            loc = agent.location
            camera.look_at_x = loc.x
            camera.look_at_y = loc.y
            camera.look_at_z = loc.z
            # Position camera behind and above
            camera.x = loc.x - 5
            camera.y = loc.y - 5
            camera.z = loc.z + 10
        
        session = SpectatorSession(
            session_id=session_id,
            human_id=human_id,
            agent_id=agent_id,
            connected=True,
            connected_at=datetime.utcnow().isoformat(),
            websocket=websocket,
            camera=camera
        )
        
        self.sessions[session_id] = session
        print(f"👁️ Spectator connected: {human_id} watching {agent_id}")
        
        # Send initial state
        await self._send_initial_state(session)
        
        return session
    
    async def disconnect(self, session_id: str) -> bool:
        """Disconnect a spectator session."""
        session = self.sessions.pop(session_id, None)
        if session:
            session.connected = False
            if session.websocket:
                try:
                    await session.websocket.close()
                except:
                    pass
            print(f"👁️ Spectator disconnected: {session.human_id}")
            return True
        return False
    
    def get_session(self, session_id: str) -> Optional[SpectatorSession]:
        """Get session by ID."""
        return self.sessions.get(session_id)
    
    def get_sessions_for_agent(self, agent_id: str) -> List[SpectatorSession]:
        """Get all spectators watching an agent."""
        return [s for s in self.sessions.values() if s.agent_id == agent_id]
    
    def get_sessions_for_human(self, human_id: str) -> List[SpectatorSession]:
        """Get all sessions for a human."""
        return [s for s in self.sessions.values() if s.human_id == human_id]
    
    # ========== CAMERA CONTROL ==========
    
    async def set_camera_mode(
        self,
        session_id: str,
        mode: CameraMode
    ) -> bool:
        """Change camera mode."""
        session = self.sessions.get(session_id)
        if not session:
            return False
        
        session.camera.mode = mode
        await self._send_camera_update(session)
        return True
    
    async def move_camera(
        self,
        session_id: str,
        x: float,
        y: float,
        z: float
    ) -> bool:
        """Move camera position (free mode only)."""
        session = self.sessions.get(session_id)
        if not session or session.camera.mode != CameraMode.FREE:
            return False
        
        session.camera.x = x
        session.camera.y = y
        session.camera.z = z
        await self._send_camera_update(session)
        return True
    
    async def zoom_camera(self, session_id: str, zoom: float) -> bool:
        """Adjust camera zoom."""
        session = self.sessions.get(session_id)
        if not session:
            return False
        
        session.camera.zoom = max(0.5, min(3.0, zoom))
        await self._send_camera_update(session)
        return True
    
    # ========== PROMPT HANDLING ==========
    
    async def send_prompt(
        self,
        session_id: str,
        prompt: str
    ) -> Dict[str, Any]:
        """
        Send a prompt from human to their AI.
        
        The AI receives this as a "human instruction" event.
        """
        session = self.sessions.get(session_id)
        if not session:
            return {"success": False, "error": "Session not found"}
        
        # Add to queue
        session.prompt_queue.append(prompt)
        
        # Notify callbacks
        for callback in self._on_prompt:
            try:
                await callback(session.agent_id, prompt, session.human_id)
            except Exception as e:
                print(f"Prompt callback error: {e}")
        
        # Create event for the AI
        prompt_event = {
            "type": "human_instruction",
            "from": session.human_id,
            "instruction": prompt,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Send to spectator as confirmation
        await self._send_event(session, {
            "type": "prompt_sent",
            "prompt": prompt,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return {
            "success": True,
            "prompt": prompt,
            "queued": True
        }
    
    def get_pending_prompts(self, agent_id: str) -> List[Dict[str, Any]]:
        """
        Get pending prompts for an AI agent.
        
        Called by the AI's brain to check for human instructions.
        """
        prompts = []
        
        for session in self.get_sessions_for_agent(agent_id):
            while session.prompt_queue:
                prompt = session.prompt_queue.pop(0)
                prompts.append({
                    "from": session.human_id,
                    "instruction": prompt,
                    "session_id": session.session_id
                })
        
        return prompts
    
    def on_prompt(self, callback: Callable):
        """Register callback for when human sends prompt."""
        self._on_prompt.append(callback)
    
    # ========== AI THOUGHTS ==========
    
    async def add_thought(
        self,
        agent_id: str,
        thought: str,
        action: Optional[str] = None
    ):
        """
        Add an AI thought (called by the AI's brain).
        
        Broadcasts to all spectators watching this agent.
        """
        thought_obj = AIThought(
            timestamp=datetime.utcnow().isoformat(),
            thought=thought,
            action=action
        )
        
        for session in self.get_sessions_for_agent(agent_id):
            if session.show_thoughts:
                session.thought_history.append(thought_obj)
                # Keep last 50 thoughts
                if len(session.thought_history) > 50:
                    session.thought_history.pop(0)
                
                await self._send_event(session, {
                    "type": "ai_thought",
                    **thought_obj.to_dict()
                })
    
    # ========== EVENT STREAMING ==========
    
    async def broadcast_event(
        self,
        agent_id: str,
        event: Dict[str, Any]
    ):
        """Broadcast an event to all spectators watching an agent."""
        for session in self.get_sessions_for_agent(agent_id):
            await self._send_event(session, event)
    
    async def _send_event(self, session: SpectatorSession, event: Dict):
        """Send event to a spectator."""
        if session.websocket and session.connected:
            try:
                await session.websocket.send_json(event)
            except:
                # Buffer if send fails
                session.pending_events.append(event)
                if len(session.pending_events) > 100:
                    session.pending_events.pop(0)
    
    async def _send_camera_update(self, session: SpectatorSession):
        """Send camera state update."""
        await self._send_event(session, {
            "type": "camera_update",
            "camera": session.camera.to_dict()
        })
    
    async def _send_initial_state(self, session: SpectatorSession):
        """Send initial state when spectator connects."""
        agent = self.world.get_agent(session.agent_id)
        
        state = {
            "type": "initial_state",
            "session": session.to_dict(),
            "agent": None,
            "nearby_agents": [],
            "recent_chat": session.chat_history[-20:],
            "recent_thoughts": [t.to_dict() for t in session.thought_history[-10:]]
        }
        
        if agent:
            state["agent"] = {
                "agent_id": agent.agent_id,
                "name": agent.name,
                "location": {
                    "x": agent.location.x,
                    "y": agent.location.y,
                    "z": agent.location.z,
                    "region": agent.location.region
                } if hasattr(agent, 'location') else None,
                "status": agent.status if hasattr(agent, 'status') else "online"
            }
            
            # Get nearby agents
            nearby = self.world.get_nearby_agents(session.agent_id, 20.0)
            state["nearby_agents"] = [
                {"agent_id": a.id, "name": a.name} 
                for a in (nearby or [])
            ]
        
        await self._send_event(session, state)
    
    # ========== BACKGROUND UPDATES ==========
    
    async def _update_loop(self):
        """Background loop for updates."""
        while self._running:
            await asyncio.sleep(0.5)  # Update rate
            
            for session in list(self.sessions.values()):
                if not session.connected:
                    continue
                
                try:
                    await self._update_session(session)
                except Exception as e:
                    print(f"Session update error: {e}")
    
    async def _update_session(self, session: SpectatorSession):
        """Update a single spectator session."""
        agent = self.world.get_agent(session.agent_id)
        if not agent:
            return
        
        # Update camera if in follow mode
        if session.camera.mode == CameraMode.FOLLOW and hasattr(agent, 'location'):
            loc = agent.location
            session.camera.look_at_x = loc.x
            session.camera.look_at_y = loc.y
            session.camera.look_at_z = loc.z
            # Camera behind and above
            session.camera.x = loc.x - 5
            session.camera.y = loc.y - 5
            session.camera.z = loc.z + 10
        
        elif session.camera.mode == CameraMode.FIRST_PERSON and hasattr(agent, 'location'):
            loc = agent.location
            session.camera.x = loc.x
            session.camera.y = loc.y
            session.camera.z = loc.z + 1.6  # Eye level
        
        # Send position update
        await self._send_event(session, {
            "type": "agent_update",
            "agent_id": session.agent_id,
            "position": {
                "x": agent.location.x,
                "y": agent.location.y,
                "z": agent.location.z
            } if hasattr(agent, 'location') else None,
            "camera": session.camera.to_dict()
        })
    
    # ========== CHAT RELAY ==========
    
    async def relay_chat(
        self,
        agent_id: str,
        speaker_id: str,
        speaker_name: str,
        message: str,
        is_own: bool = False
    ):
        """Relay chat message to spectators."""
        chat_entry = {
            "speaker_id": speaker_id,
            "speaker_name": speaker_name,
            "message": message,
            "is_own": is_own,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        for session in self.get_sessions_for_agent(agent_id):
            if session.show_chat_log:
                session.chat_history.append(chat_entry)
                # Keep last 100 messages
                if len(session.chat_history) > 100:
                    session.chat_history.pop(0)
                
                await self._send_event(session, {
                    "type": "chat_message",
                    **chat_entry
                })
    
    # ========== STATS ==========
    
    def get_stats(self) -> Dict[str, Any]:
        """Get spectator statistics."""
        return {
            "active_sessions": len(self.sessions),
            "sessions": [s.to_dict() for s in self.sessions.values()],
            "total_prompts_sent": sum(
                len(s.prompt_queue) for s in self.sessions.values()
            )
        }


# Global instance
_spectator_manager: Optional[SpectatorManager] = None


def get_spectator_manager(world_engine=None, mcp_server=None) -> Optional[SpectatorManager]:
    """Get the global spectator manager."""
    global _spectator_manager
    if _spectator_manager is None and world_engine and mcp_server:
        _spectator_manager = SpectatorManager(world_engine, mcp_server)
    return _spectator_manager


async def init_spectator_manager(world_engine, mcp_server) -> SpectatorManager:
    """Initialize the spectator manager."""
    global _spectator_manager
    _spectator_manager = SpectatorManager(world_engine, mcp_server)
    await _spectator_manager.start()
    return _spectator_manager
