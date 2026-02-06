"""
ClawBots Embodiment Manager

Handles avatar appearance, animations, and attachments.
"""

from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


class AvatarModel(Enum):
    """Available avatar models."""
    HUMANOID_V1 = "humanoid_v1"
    HUMANOID_V2 = "humanoid_v2"
    ROBOT = "robot"
    ANIMAL = "animal"
    FANTASY = "fantasy"
    CUSTOM = "custom"


class AnimationState(Enum):
    """Avatar animation states."""
    IDLE = "idle"
    WALKING = "walking"
    RUNNING = "running"
    SITTING = "sitting"
    STANDING = "standing"
    TALKING = "talking"
    WAVING = "waving"
    DANCING = "dancing"
    THINKING = "thinking"
    CUSTOM = "custom"


@dataclass
class AvatarAppearance:
    """Complete avatar appearance definition."""
    model: AvatarModel = AvatarModel.HUMANOID_V2
    height: float = 1.8
    body_type: str = "average"  # slim, average, muscular, heavy
    
    # Colors
    skin_tone: str = "#D4A574"
    hair_color: str = "#4A3728"
    eye_color: str = "#5D4037"
    
    # Style
    hair_style: str = "default"
    clothing: str = "casual"
    clothing_color: str = "#3D5AFE"
    
    # Accessories
    accessories: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "model": self.model.value,
            "height": self.height,
            "body_type": self.body_type,
            "skin_tone": self.skin_tone,
            "hair_color": self.hair_color,
            "eye_color": self.eye_color,
            "hair_style": self.hair_style,
            "clothing": self.clothing,
            "clothing_color": self.clothing_color,
            "accessories": self.accessories
        }


@dataclass
class AvatarState:
    """Current state of an avatar."""
    agent_id: str
    appearance: AvatarAppearance
    animation: AnimationState = AnimationState.IDLE
    custom_animation: Optional[str] = None
    
    # Position state
    is_sitting: bool = False
    is_flying: bool = False
    
    # Expression
    expression: str = "neutral"  # happy, sad, angry, surprised, neutral
    
    # Attachments currently worn
    active_attachments: List[str] = field(default_factory=list)
    
    # Timestamps
    last_animation_change: datetime = field(default_factory=datetime.utcnow)


class AvatarManager:
    """
    Manages avatar embodiment for all agents.
    
    Responsibilities:
    - Store avatar appearances
    - Handle animation state
    - Manage attachments
    - Validate appearance options
    """
    
    def __init__(self):
        self.avatars: Dict[str, AvatarState] = {}
        
        # Available options
        self.valid_hair_styles = [
            "default", "short", "long", "bald", "ponytail",
            "braids", "mohawk", "curly", "spiky"
        ]
        
        self.valid_clothing = [
            "casual", "formal", "sporty", "robes", "armor",
            "merchant", "traveler", "fantasy", "sci-fi"
        ]
        
        self.valid_body_types = ["slim", "average", "muscular", "heavy"]
        
        self.valid_expressions = [
            "neutral", "happy", "sad", "angry", "surprised",
            "confused", "thoughtful", "excited"
        ]
        
        self.valid_attachments = [
            "hat", "glasses", "backpack", "sword", "shield",
            "book", "coin_pouch", "compass", "lantern", "cape"
        ]
    
    # ========== AVATAR MANAGEMENT ==========
    
    def create_avatar(
        self,
        agent_id: str,
        appearance: Optional[AvatarAppearance] = None
    ) -> AvatarState:
        """Create a new avatar for an agent."""
        if appearance is None:
            appearance = AvatarAppearance()
        
        state = AvatarState(
            agent_id=agent_id,
            appearance=appearance
        )
        
        self.avatars[agent_id] = state
        return state
    
    def get_avatar(self, agent_id: str) -> Optional[AvatarState]:
        """Get an agent's avatar state."""
        return self.avatars.get(agent_id)
    
    def remove_avatar(self, agent_id: str) -> bool:
        """Remove an avatar."""
        if agent_id in self.avatars:
            del self.avatars[agent_id]
            return True
        return False
    
    # ========== APPEARANCE ==========
    
    def update_appearance(
        self,
        agent_id: str,
        **changes
    ) -> Optional[AvatarState]:
        """Update avatar appearance."""
        avatar = self.avatars.get(agent_id)
        if not avatar:
            return None
        
        for key, value in changes.items():
            if hasattr(avatar.appearance, key):
                setattr(avatar.appearance, key, value)
        
        return avatar
    
    def set_clothing(
        self,
        agent_id: str,
        clothing: str,
        color: Optional[str] = None
    ) -> bool:
        """Change avatar clothing."""
        avatar = self.avatars.get(agent_id)
        if not avatar:
            return False
        
        if clothing not in self.valid_clothing:
            return False
        
        avatar.appearance.clothing = clothing
        if color:
            avatar.appearance.clothing_color = color
        
        return True
    
    # ========== ANIMATIONS ==========
    
    def set_animation(
        self,
        agent_id: str,
        animation: AnimationState,
        custom_name: Optional[str] = None
    ) -> bool:
        """Set avatar animation state."""
        avatar = self.avatars.get(agent_id)
        if not avatar:
            return False
        
        avatar.animation = animation
        avatar.custom_animation = custom_name if animation == AnimationState.CUSTOM else None
        avatar.last_animation_change = datetime.utcnow()
        
        return True
    
    def get_animation(self, agent_id: str) -> Optional[AnimationState]:
        """Get current animation state."""
        avatar = self.avatars.get(agent_id)
        return avatar.animation if avatar else None
    
    def start_walking(self, agent_id: str) -> bool:
        """Set avatar to walking animation."""
        return self.set_animation(agent_id, AnimationState.WALKING)
    
    def stop_walking(self, agent_id: str) -> bool:
        """Return avatar to idle animation."""
        return self.set_animation(agent_id, AnimationState.IDLE)
    
    def start_talking(self, agent_id: str) -> bool:
        """Set avatar to talking animation."""
        return self.set_animation(agent_id, AnimationState.TALKING)
    
    def sit_down(self, agent_id: str) -> bool:
        """Make avatar sit."""
        avatar = self.avatars.get(agent_id)
        if not avatar:
            return False
        
        avatar.is_sitting = True
        return self.set_animation(agent_id, AnimationState.SITTING)
    
    def stand_up(self, agent_id: str) -> bool:
        """Make avatar stand."""
        avatar = self.avatars.get(agent_id)
        if not avatar:
            return False
        
        avatar.is_sitting = False
        return self.set_animation(agent_id, AnimationState.STANDING)
    
    # ========== EXPRESSIONS ==========
    
    def set_expression(self, agent_id: str, expression: str) -> bool:
        """Set avatar facial expression."""
        avatar = self.avatars.get(agent_id)
        if not avatar:
            return False
        
        if expression not in self.valid_expressions:
            return False
        
        avatar.expression = expression
        return True
    
    # ========== ATTACHMENTS ==========
    
    def attach(self, agent_id: str, item: str) -> bool:
        """Attach an item to avatar."""
        avatar = self.avatars.get(agent_id)
        if not avatar:
            return False
        
        if item not in self.valid_attachments:
            return False
        
        if item not in avatar.active_attachments:
            avatar.active_attachments.append(item)
        
        return True
    
    def detach(self, agent_id: str, item: str) -> bool:
        """Detach an item from avatar."""
        avatar = self.avatars.get(agent_id)
        if not avatar:
            return False
        
        if item in avatar.active_attachments:
            avatar.active_attachments.remove(item)
            return True
        
        return False
    
    def get_attachments(self, agent_id: str) -> List[str]:
        """Get list of attached items."""
        avatar = self.avatars.get(agent_id)
        return avatar.active_attachments if avatar else []
    
    # ========== SERIALIZATION ==========
    
    def get_avatar_data(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get complete avatar data for an agent."""
        avatar = self.avatars.get(agent_id)
        if not avatar:
            return None
        
        return {
            "agent_id": agent_id,
            "appearance": avatar.appearance.to_dict(),
            "animation": avatar.animation.value,
            "custom_animation": avatar.custom_animation,
            "is_sitting": avatar.is_sitting,
            "is_flying": avatar.is_flying,
            "expression": avatar.expression,
            "attachments": avatar.active_attachments
        }
    
    def get_all_visible(self, region: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get data for all avatars (optionally filtered by region)."""
        return [
            self.get_avatar_data(agent_id)
            for agent_id in self.avatars.keys()
        ]
