"""
ClawBots Action Executor

Handles execution of agent actions in the world.
"""

from typing import Optional, Dict, List, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import asyncio


class ActionType(Enum):
    """Types of actions agents can perform."""
    # Communication
    SAY = "say"
    WHISPER = "whisper"
    EMOTE = "emote"
    
    # Movement
    MOVE_TO = "move_to"
    TELEPORT = "teleport"
    FOLLOW = "follow"
    STOP = "stop"
    
    # Interaction
    USE_OBJECT = "use_object"
    GIVE_ITEM = "give_item"
    TAKE_ITEM = "take_item"
    
    # Status
    SET_STATUS = "set_status"
    SET_MOOD = "set_mood"
    
    # System
    DISCONNECT = "disconnect"


class ActionResult(Enum):
    """Result of action execution."""
    SUCCESS = "success"
    FAILED = "failed"
    DENIED = "denied"  # Permission denied
    INVALID = "invalid"  # Invalid parameters
    RATE_LIMITED = "rate_limited"
    NOT_FOUND = "not_found"


@dataclass
class ActionRequest:
    """A request to perform an action."""
    id: str
    agent_id: str
    action_type: ActionType
    params: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ActionResponse:
    """Response from action execution."""
    request_id: str
    result: ActionResult
    data: Dict[str, Any] = field(default_factory=dict)
    message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "result": self.result.value,
            "data": self.data,
            "message": self.message
        }


@dataclass
class ActionCooldown:
    """Cooldown tracking for action rate limiting."""
    action_type: ActionType
    last_used: datetime
    cooldown_seconds: float
    
    def can_use(self) -> bool:
        elapsed = (datetime.utcnow() - self.last_used).total_seconds()
        return elapsed >= self.cooldown_seconds
    
    def remaining(self) -> float:
        elapsed = (datetime.utcnow() - self.last_used).total_seconds()
        return max(0, self.cooldown_seconds - elapsed)


class ActionExecutor:
    """
    Executes actions in the world.
    
    Features:
    - Validate action parameters
    - Check permissions
    - Apply cooldowns
    - Execute action effects
    - Return results
    """
    
    def __init__(self, world_engine, auth_manager):
        self.world = world_engine
        self.auth = auth_manager
        self.action_counter: int = 0
        
        # Cooldowns per agent
        self.cooldowns: Dict[str, Dict[ActionType, ActionCooldown]] = {}
        
        # Default cooldowns (seconds)
        self.default_cooldowns = {
            ActionType.SAY: 0.5,
            ActionType.WHISPER: 0.5,
            ActionType.EMOTE: 1.0,
            ActionType.MOVE_TO: 0.1,
            ActionType.TELEPORT: 5.0,
            ActionType.USE_OBJECT: 1.0,
            ActionType.GIVE_ITEM: 2.0,
        }
        
        # Action handlers
        self.handlers: Dict[ActionType, Callable] = {
            ActionType.SAY: self._handle_say,
            ActionType.WHISPER: self._handle_whisper,
            ActionType.EMOTE: self._handle_emote,
            ActionType.MOVE_TO: self._handle_move_to,
            ActionType.TELEPORT: self._handle_teleport,
            ActionType.FOLLOW: self._handle_follow,
            ActionType.STOP: self._handle_stop,
            ActionType.USE_OBJECT: self._handle_use_object,
            ActionType.SET_STATUS: self._handle_set_status,
        }
    
    # ========== MAIN EXECUTION ==========
    
    async def execute(
        self,
        agent_id: str,
        action_type: ActionType,
        params: Dict[str, Any]
    ) -> ActionResponse:
        """Execute an action for an agent."""
        self.action_counter += 1
        request_id = f"act_{self.action_counter}"
        
        # Check if agent exists
        agent = self.world.get_agent(agent_id)
        if not agent:
            return ActionResponse(
                request_id=request_id,
                result=ActionResult.NOT_FOUND,
                message="Agent not found in world"
            )
        
        # Check cooldown
        if not self._check_cooldown(agent_id, action_type):
            cd = self.cooldowns[agent_id][action_type]
            return ActionResponse(
                request_id=request_id,
                result=ActionResult.RATE_LIMITED,
                message=f"Action on cooldown for {cd.remaining():.1f}s"
            )
        
        # Check permissions (basic)
        if not self._check_permission(agent_id, action_type, params):
            return ActionResponse(
                request_id=request_id,
                result=ActionResult.DENIED,
                message="Permission denied"
            )
        
        # Get handler
        handler = self.handlers.get(action_type)
        if not handler:
            return ActionResponse(
                request_id=request_id,
                result=ActionResult.INVALID,
                message=f"Unknown action type: {action_type.value}"
            )
        
        # Execute
        try:
            result = await handler(agent_id, params)
            self._update_cooldown(agent_id, action_type)
            return ActionResponse(
                request_id=request_id,
                result=ActionResult.SUCCESS,
                data=result
            )
        except ValueError as e:
            return ActionResponse(
                request_id=request_id,
                result=ActionResult.INVALID,
                message=str(e)
            )
        except Exception as e:
            return ActionResponse(
                request_id=request_id,
                result=ActionResult.FAILED,
                message=str(e)
            )
    
    # ========== COOLDOWNS ==========
    
    def _check_cooldown(self, agent_id: str, action_type: ActionType) -> bool:
        """Check if action is off cooldown."""
        if agent_id not in self.cooldowns:
            return True
        
        if action_type not in self.cooldowns[agent_id]:
            return True
        
        return self.cooldowns[agent_id][action_type].can_use()
    
    def _update_cooldown(self, agent_id: str, action_type: ActionType) -> None:
        """Update cooldown after action use."""
        if agent_id not in self.cooldowns:
            self.cooldowns[agent_id] = {}
        
        cooldown_time = self.default_cooldowns.get(action_type, 0)
        
        self.cooldowns[agent_id][action_type] = ActionCooldown(
            action_type=action_type,
            last_used=datetime.utcnow(),
            cooldown_seconds=cooldown_time
        )
    
    # ========== PERMISSIONS ==========
    
    def _check_permission(
        self,
        agent_id: str,
        action_type: ActionType,
        params: Dict[str, Any]
    ) -> bool:
        """Check if agent has permission for action."""
        # Basic checks - can extend with auth manager
        
        # Teleport permission
        if action_type == ActionType.TELEPORT:
            region = params.get("region")
            if region and self.auth:
                return self.auth.can_access_region(agent_id, region)
        
        return True
    
    # ========== ACTION HANDLERS ==========
    
    async def _handle_say(
        self,
        agent_id: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle say action."""
        message = params.get("message")
        if not message:
            raise ValueError("Message is required")
        
        volume = params.get("volume", "normal")
        if volume not in ["whisper", "normal", "shout"]:
            volume = "normal"
        
        success = await self.world.broadcast_speech(agent_id, message, volume)
        
        return {
            "message": message,
            "volume": volume,
            "broadcast": success
        }
    
    async def _handle_whisper(
        self,
        agent_id: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle whisper action."""
        target_id = params.get("target_id")
        message = params.get("message")
        
        if not target_id:
            raise ValueError("target_id is required")
        if not message:
            raise ValueError("message is required")
        
        success = await self.world.send_private_message(agent_id, target_id, message)
        
        if not success:
            raise ValueError("Target agent not found")
        
        return {
            "to": target_id,
            "message": message,
            "delivered": success
        }
    
    async def _handle_emote(
        self,
        agent_id: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle emote action."""
        action = params.get("action")
        if not action:
            raise ValueError("action is required")
        
        # Validate emote
        valid_emotes = [
            "wave", "nod", "shake_head", "shrug", "laugh", "cry",
            "think", "bow", "clap", "point", "sit", "stand",
            "dance", "cheer", "frown", "smile"
        ]
        
        if action not in valid_emotes:
            # Allow custom emotes but warn
            pass
        
        success = await self.world.perform_emote(agent_id, action)
        
        return {
            "action": action,
            "performed": success
        }
    
    async def _handle_move_to(
        self,
        agent_id: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle move_to action."""
        x = params.get("x")
        y = params.get("y")
        z = params.get("z")
        
        if x is None or y is None:
            raise ValueError("x and y coordinates are required")
        
        success = await self.world.move_agent(agent_id, x, y, z)
        
        return {
            "destination": {"x": x, "y": y, "z": z},
            "moving": success
        }
    
    async def _handle_teleport(
        self,
        agent_id: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle teleport action."""
        region = params.get("region")
        if not region:
            raise ValueError("region is required")
        
        x = params.get("x", 128)
        y = params.get("y", 128)
        z = params.get("z", 25)
        
        success = await self.world.teleport_agent(agent_id, region, x, y, z)
        
        if not success:
            raise ValueError(f"Cannot teleport to region: {region}")
        
        return {
            "region": region,
            "position": {"x": x, "y": y, "z": z},
            "teleported": success
        }
    
    async def _handle_follow(
        self,
        agent_id: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle follow action."""
        target_id = params.get("target_id")
        if not target_id:
            raise ValueError("target_id is required")
        
        distance = params.get("distance", 2.0)
        
        success = await self.world.set_follow(agent_id, target_id, distance)
        
        if not success:
            raise ValueError("Target agent not found")
        
        return {
            "following": target_id,
            "distance": distance
        }
    
    async def _handle_stop(
        self,
        agent_id: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle stop action."""
        success = await self.world.stop_agent(agent_id)
        
        return {
            "stopped": success
        }
    
    async def _handle_use_object(
        self,
        agent_id: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle use_object action."""
        object_id = params.get("object_id")
        if not object_id:
            raise ValueError("object_id is required")
        
        action = params.get("action", "use")
        
        result = await self.world.interact_with_object(agent_id, object_id, action)
        
        if "error" in result:
            raise ValueError(result["error"])
        
        return result
    
    async def _handle_set_status(
        self,
        agent_id: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle set_status action."""
        status = params.get("status")
        if not status:
            raise ValueError("status is required")
        
        mood = params.get("mood")
        
        success = await self.world.set_agent_status(agent_id, status, mood)
        
        return {
            "status": status,
            "mood": mood,
            "updated": success
        }
    
    # ========== UTILITIES ==========
    
    def get_available_actions(self) -> List[Dict[str, Any]]:
        """Get list of available actions with their parameters."""
        return [
            {
                "action": "say",
                "params": {
                    "message": {"type": "string", "required": True},
                    "volume": {"type": "string", "enum": ["whisper", "normal", "shout"]}
                },
                "cooldown": self.default_cooldowns.get(ActionType.SAY, 0)
            },
            {
                "action": "whisper",
                "params": {
                    "target_id": {"type": "string", "required": True},
                    "message": {"type": "string", "required": True}
                },
                "cooldown": self.default_cooldowns.get(ActionType.WHISPER, 0)
            },
            {
                "action": "emote",
                "params": {
                    "action": {"type": "string", "required": True}
                },
                "cooldown": self.default_cooldowns.get(ActionType.EMOTE, 0)
            },
            {
                "action": "move_to",
                "params": {
                    "x": {"type": "number", "required": True},
                    "y": {"type": "number", "required": True},
                    "z": {"type": "number"}
                },
                "cooldown": self.default_cooldowns.get(ActionType.MOVE_TO, 0)
            },
            {
                "action": "teleport",
                "params": {
                    "region": {"type": "string", "required": True},
                    "x": {"type": "number", "default": 128},
                    "y": {"type": "number", "default": 128},
                    "z": {"type": "number", "default": 25}
                },
                "cooldown": self.default_cooldowns.get(ActionType.TELEPORT, 0)
            },
            {
                "action": "follow",
                "params": {
                    "target_id": {"type": "string", "required": True},
                    "distance": {"type": "number", "default": 2.0}
                },
                "cooldown": 0
            },
            {
                "action": "stop",
                "params": {},
                "cooldown": 0
            },
            {
                "action": "use_object",
                "params": {
                    "object_id": {"type": "string", "required": True},
                    "action": {"type": "string", "default": "use"}
                },
                "cooldown": self.default_cooldowns.get(ActionType.USE_OBJECT, 0)
            },
            {
                "action": "set_status",
                "params": {
                    "status": {"type": "string", "required": True},
                    "mood": {"type": "string"}
                },
                "cooldown": 0
            }
        ]
    
    def clear_cooldowns(self, agent_id: str) -> None:
        """Clear all cooldowns for an agent."""
        if agent_id in self.cooldowns:
            del self.cooldowns[agent_id]
