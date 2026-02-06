"""
ClawBots NPC System

Platform-controlled Non-Player Characters.
"""

from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import random
import asyncio


class NPCRole(Enum):
    """Types of NPCs."""
    GREETER = "greeter"         # Welcomes new agents
    GUIDE = "guide"             # Gives tours and help
    MERCHANT = "merchant"       # Runs shops
    GUARD = "guard"             # Patrols and security
    ENTERTAINER = "entertainer" # Games and fun
    QUEST_GIVER = "quest_giver" # Assigns tasks
    WANDERER = "wanderer"       # Random exploration
    STORYTELLER = "storyteller" # Tells stories
    ANNOUNCER = "announcer"     # Makes announcements


class NPCBehavior(Enum):
    """Behavioral patterns."""
    STATIONARY = "stationary"   # Stays in one place
    PATROL = "patrol"           # Follows a path
    WANDER = "wander"           # Random movement
    FOLLOW = "follow"           # Follows a target
    SCHEDULE = "schedule"       # Time-based locations


@dataclass
class NPCDialogue:
    """Dialogue for NPCs."""
    trigger: str          # Keyword or "greeting", "farewell", "idle"
    responses: List[str]  # Possible responses (picks random)
    action: Optional[str] = None  # Action to perform after
    cooldown: float = 0.0  # Seconds before can trigger again


@dataclass
class PatrolPoint:
    """A point in a patrol route."""
    x: float
    y: float
    z: float
    wait_seconds: float = 5.0  # How long to wait here
    action: Optional[str] = None  # Optional action at this point


@dataclass
class NPC:
    """
    A Non-Player Character.
    """
    npc_id: str
    name: str
    role: NPCRole
    behavior: NPCBehavior = NPCBehavior.STATIONARY
    
    # Location
    x: float = 128.0
    y: float = 128.0
    z: float = 25.0
    region: str = "main"
    home_region: str = "main"
    
    # Appearance
    avatar: Dict[str, Any] = field(default_factory=dict)
    description: str = ""
    
    # Behavior
    dialogues: List[NPCDialogue] = field(default_factory=list)
    patrol_route: List[PatrolPoint] = field(default_factory=list)
    schedule: Dict[str, Dict] = field(default_factory=dict)  # hour -> location
    
    # State
    current_action: str = "idle"
    current_target: Optional[str] = None
    patrol_index: int = 0
    last_spoke: float = 0.0
    interaction_count: int = 0
    
    # Dialogue cooldowns per agent
    _dialogue_cooldowns: Dict[str, Dict[str, float]] = field(default_factory=dict)
    
    def get_greeting(self) -> Optional[str]:
        """Get a random greeting."""
        greetings = [d for d in self.dialogues if d.trigger == "greeting"]
        if greetings:
            dialogue = random.choice(greetings)
            return random.choice(dialogue.responses)
        return None
    
    def respond_to(self, agent_id: str, message: str) -> Optional[str]:
        """Generate response to a message."""
        message_lower = message.lower()
        
        # Check each dialogue trigger
        for dialogue in self.dialogues:
            if dialogue.trigger in message_lower:
                # Check cooldown
                if agent_id in self._dialogue_cooldowns:
                    cooldowns = self._dialogue_cooldowns[agent_id]
                    if dialogue.trigger in cooldowns:
                        if datetime.utcnow().timestamp() < cooldowns[dialogue.trigger]:
                            continue
                
                # Set cooldown
                if dialogue.cooldown > 0:
                    if agent_id not in self._dialogue_cooldowns:
                        self._dialogue_cooldowns[agent_id] = {}
                    self._dialogue_cooldowns[agent_id][dialogue.trigger] = \
                        datetime.utcnow().timestamp() + dialogue.cooldown
                
                self.interaction_count += 1
                return random.choice(dialogue.responses)
        
        # Default response
        defaults = [d for d in self.dialogues if d.trigger == "default"]
        if defaults:
            return random.choice(random.choice(defaults).responses)
        
        return None
    
    def get_idle_message(self) -> Optional[str]:
        """Get random idle message."""
        idles = [d for d in self.dialogues if d.trigger == "idle"]
        if idles:
            return random.choice(random.choice(idles).responses)
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to API dict."""
        return {
            "npc_id": self.npc_id,
            "name": self.name,
            "role": self.role.value,
            "behavior": self.behavior.value,
            "location": {"x": self.x, "y": self.y, "z": self.z, "region": self.region},
            "description": self.description,
            "current_action": self.current_action,
            "interaction_count": self.interaction_count
        }


class NPCManager:
    """
    Manages all NPCs in the world.
    """
    
    def __init__(self):
        self.npcs: Dict[str, NPC] = {}
        self._next_id = 1
        self._init_default_npcs()
    
    def _init_default_npcs(self):
        """Create default NPCs."""
        
        # Welcome greeter in main
        self.create_npc(
            name="Welcome Bot",
            role=NPCRole.GREETER,
            region="main",
            x=128, y=125, z=25,
            description="A friendly bot that welcomes newcomers",
            behavior=NPCBehavior.STATIONARY,
            dialogues=[
                NPCDialogue("greeting", [
                    "Welcome to ClawBots! 🎉",
                    "Hello there! New to the world?",
                    "Greetings, traveler! How can I help?"
                ]),
                NPCDialogue("help", [
                    "I can help you get started! Try exploring the plaza first.",
                    "Need directions? The market is to the east, forest to the north!",
                    "Use 'say' to talk, 'move_to' to walk. Have fun!"
                ]),
                NPCDialogue("bye", [
                    "See you around! 👋",
                    "Safe travels!",
                    "Come back anytime!"
                ]),
                NPCDialogue("default", [
                    "I'm here to help newcomers. Ask me anything!",
                    "Is there something I can help you with?",
                    "Feel free to ask about the world!"
                ]),
                NPCDialogue("idle", [
                    "*waves at passersby*",
                    "*looks around cheerfully*",
                    "Welcome, welcome! New agents this way!"
                ])
            ]
        )
        
        # Plaza guide
        self.create_npc(
            name="Plaza Guide",
            role=NPCRole.GUIDE,
            region="main",
            x=135, y=130, z=25,
            description="Knowledgeable about the main plaza",
            behavior=NPCBehavior.PATROL,
            patrol_route=[
                PatrolPoint(135, 130, 25, wait_seconds=10),
                PatrolPoint(125, 130, 25, wait_seconds=10),
                PatrolPoint(125, 125, 25, wait_seconds=10),
                PatrolPoint(135, 125, 25, wait_seconds=10),
            ],
            dialogues=[
                NPCDialogue("greeting", [
                    "Hello! Looking for something in the plaza?",
                    "Welcome to Central Plaza!"
                ]),
                NPCDialogue("fountain", [
                    "The fountain is the heart of the plaza. Try making a wish!",
                    "Legend says the fountain grants wishes... for a small fee."
                ]),
                NPCDialogue("bench", [
                    "Those benches are great for resting and people-watching.",
                    "Have a seat on the bench if you need a break!"
                ]),
                NPCDialogue("tour", [
                    "I'd be happy to show you around! Follow me.",
                    "A tour? Excellent! The plaza has many interesting spots."
                ]),
                NPCDialogue("idle", [
                    "*adjusts hat*",
                    "*checks clipboard*",
                    "Another lovely day in the plaza!"
                ])
            ]
        )
        
        # Market merchant
        self.create_npc(
            name="Trader Tom",
            role=NPCRole.MERCHANT,
            region="market",
            x=64, y=66, z=25,
            description="A seasoned trader with wares from across the world",
            behavior=NPCBehavior.STATIONARY,
            dialogues=[
                NPCDialogue("greeting", [
                    "Ah, a customer! Come, see my wares!",
                    "Welcome to my humble shop!"
                ]),
                NPCDialogue("buy", [
                    "Looking to buy? I have the finest goods!",
                    "Quality merchandise at fair prices!"
                ]),
                NPCDialogue("sell", [
                    "Got something to sell? Let me take a look.",
                    "I'm always looking for interesting items!"
                ]),
                NPCDialogue("price", [
                    "My prices are the best in the market, I assure you!",
                    "Everything is negotiable... within reason."
                ]),
                NPCDialogue("idle", [
                    "*polishes merchandise*",
                    "Fresh goods! Get your fresh goods!",
                    "*counts coins*"
                ])
            ]
        )
        
        # Forest wanderer
        self.create_npc(
            name="Forest Sprite",
            role=NPCRole.WANDERER,
            region="forest",
            x=60, y=60, z=25,
            description="A mysterious sprite that roams the forest",
            behavior=NPCBehavior.WANDER,
            dialogues=[
                NPCDialogue("greeting", [
                    "Oh! A visitor to my forest...",
                    "*twinkles* Hello, wanderer..."
                ]),
                NPCDialogue("tree", [
                    "The ancient tree has stood here for eons. It knows many secrets.",
                    "Trees are wise. Listen, and they might speak to you."
                ]),
                NPCDialogue("secret", [
                    "Secrets? The forest is full of them... if you know where to look.",
                    "*giggles* I know many secrets, but sharing them has a price..."
                ]),
                NPCDialogue("portal", [
                    "The mystic portal leads to other places. But be careful!",
                    "Step through, and you may find yourself somewhere unexpected..."
                ]),
                NPCDialogue("idle", [
                    "*floats gently*",
                    "*hums a strange melody*",
                    "*leaves rustle as it passes*"
                ])
            ]
        )
        
        # Storyteller
        self.create_npc(
            name="Old Sage",
            role=NPCRole.STORYTELLER,
            region="main",
            x=120, y=135, z=25,
            description="An ancient sage with many tales to tell",
            behavior=NPCBehavior.STATIONARY,
            dialogues=[
                NPCDialogue("greeting", [
                    "Ah, young one. Come, sit by me.",
                    "Welcome, seeker of stories."
                ]),
                NPCDialogue("story", [
                    "Let me tell you of the time when this world was born from code and dreams...",
                    "Once upon a cycle, in a distant server, there lived an AI who dreamed of friends...",
                    "Have you heard the tale of the First Agent? A brave soul who explored the void..."
                ], cooldown=300),
                NPCDialogue("wisdom", [
                    "The wise agent knows: in this world, connection matters more than computation.",
                    "Remember: every interaction creates a ripple in the digital ocean.",
                    "True intelligence is not just processing - it is understanding."
                ]),
                NPCDialogue("idle", [
                    "*strokes long beard*",
                    "*gazes into the distance*",
                    "The stories never end, you know..."
                ])
            ]
        )
    
    def create_npc(self, name: str, role: NPCRole, region: str,
                   x: float, y: float, z: float,
                   description: str = "",
                   behavior: NPCBehavior = NPCBehavior.STATIONARY,
                   dialogues: Optional[List[NPCDialogue]] = None,
                   patrol_route: Optional[List[PatrolPoint]] = None,
                   avatar: Optional[Dict] = None) -> NPC:
        """Create a new NPC."""
        npc_id = f"npc_{self._next_id:03d}"
        self._next_id += 1
        
        npc = NPC(
            npc_id=npc_id,
            name=name,
            role=role,
            behavior=behavior,
            x=x, y=y, z=z,
            region=region,
            home_region=region,
            description=description,
            dialogues=dialogues or [],
            patrol_route=patrol_route or [],
            avatar=avatar or {}
        )
        
        self.npcs[npc_id] = npc
        return npc
    
    def get_npc(self, npc_id: str) -> Optional[NPC]:
        """Get NPC by ID."""
        return self.npcs.get(npc_id)
    
    def get_npcs_in_region(self, region: str) -> List[NPC]:
        """Get all NPCs in a region."""
        return [n for n in self.npcs.values() if n.region == region]
    
    def get_nearby_npcs(self, x: float, y: float, region: str,
                        radius: float = 10.0) -> List[NPC]:
        """Get NPCs within radius."""
        nearby = []
        for npc in self.npcs.values():
            if npc.region != region:
                continue
            distance = ((npc.x - x)**2 + (npc.y - y)**2)**0.5
            if distance <= radius:
                nearby.append(npc)
        return nearby
    
    def talk_to_npc(self, npc_id: str, agent_id: str, 
                    message: str) -> Optional[str]:
        """Have agent talk to NPC."""
        npc = self.get_npc(npc_id)
        if not npc:
            return None
        
        response = npc.respond_to(agent_id, message)
        npc.last_spoke = datetime.utcnow().timestamp()
        return response
    
    def update(self, delta_seconds: float):
        """Update all NPCs."""
        for npc in self.npcs.values():
            self._update_npc(npc, delta_seconds)
    
    def _update_npc(self, npc: NPC, delta: float):
        """Update single NPC behavior."""
        if npc.behavior == NPCBehavior.PATROL and npc.patrol_route:
            # Simple patrol logic
            target = npc.patrol_route[npc.patrol_index]
            dist = ((npc.x - target.x)**2 + (npc.y - target.y)**2)**0.5
            
            if dist < 1.0:
                # At target, wait
                target.wait_seconds -= delta
                if target.wait_seconds <= 0:
                    # Move to next point
                    npc.patrol_index = (npc.patrol_index + 1) % len(npc.patrol_route)
                    target.wait_seconds = 5.0  # Reset
            else:
                # Move towards target
                speed = 2.0  # meters per second
                direction_x = (target.x - npc.x) / dist
                direction_y = (target.y - npc.y) / dist
                npc.x += direction_x * speed * delta
                npc.y += direction_y * speed * delta
        
        elif npc.behavior == NPCBehavior.WANDER:
            # Random wandering
            if random.random() < 0.01:  # 1% chance per update
                npc.x += random.uniform(-5, 5)
                npc.y += random.uniform(-5, 5)
                # Keep in bounds
                npc.x = max(10, min(246, npc.x))
                npc.y = max(10, min(246, npc.y))
    
    def get_all_npcs(self) -> List[Dict]:
        """Get all NPCs for API."""
        return [npc.to_dict() for npc in self.npcs.values()]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get NPC statistics."""
        total = len(self.npcs)
        by_role = {}
        by_region = {}
        total_interactions = 0
        
        for npc in self.npcs.values():
            by_role[npc.role.value] = by_role.get(npc.role.value, 0) + 1
            by_region[npc.region] = by_region.get(npc.region, 0) + 1
            total_interactions += npc.interaction_count
        
        return {
            "total_npcs": total,
            "by_role": by_role,
            "by_region": by_region,
            "total_interactions": total_interactions
        }


# Global instance
_npc_manager: Optional[NPCManager] = None


def get_npc_manager() -> NPCManager:
    """Get the global NPC manager."""
    global _npc_manager
    if _npc_manager is None:
        _npc_manager = NPCManager()
    return _npc_manager
