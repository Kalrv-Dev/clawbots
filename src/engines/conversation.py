"""Conversation Orchestration Engine (RFC-0004)

Manages multi-agent conversations:
- Turn taking & interruptions
- Silence as valid action
- Topic threading
- Natural flow
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import random

@dataclass
class Message:
    id: str
    speaker_id: str
    speaker_name: str
    content: str
    timestamp: datetime
    reply_to: Optional[str] = None
    importance: float = 0.5

@dataclass
class ConversationState:
    messages: List[Message] = field(default_factory=list)
    participants: Dict[str, datetime] = field(default_factory=dict)  # agent_id -> last_spoke
    topic: Optional[str] = None
    started_at: Optional[datetime] = None
    
    @property
    def is_active(self) -> bool:
        if not self.messages:
            return False
        last_msg_time = self.messages[-1].timestamp
        return datetime.now() - last_msg_time < timedelta(minutes=5)
    
    def time_since_last_spoke(self, agent_id: str) -> float:
        """Seconds since agent last spoke"""
        if agent_id not in self.participants:
            return float('inf')
        return (datetime.now() - self.participants[agent_id]).total_seconds()

class ConversationOrchestrator:
    """Manages who speaks when in multi-agent conversations"""
    
    def __init__(self):
        self.conversations: Dict[str, ConversationState] = {}
        self.min_response_delay = 1.0  # seconds
        self.max_response_delay = 5.0
        self.silence_threshold = 0.3  # Below this, agent stays silent
    
    def get_or_create(self, location: str) -> ConversationState:
        """Get conversation at location or create new"""
        if location not in self.conversations:
            self.conversations[location] = ConversationState(started_at=datetime.now())
        return self.conversations[location]
    
    def add_message(self, location: str, message: Message):
        """Add message to conversation"""
        conv = self.get_or_create(location)
        conv.messages.append(message)
        conv.participants[message.speaker_id] = message.timestamp
    
    def should_respond(
        self,
        agent_id: str,
        agent_drives: Dict[str, float],
        agent_state: Dict[str, float],
        location: str
    ) -> Tuple[bool, float, str]:
        """
        Determine if agent should respond.
        Returns: (should_speak, urgency, reason)
        """
        conv = self.get_or_create(location)
        
        # No conversation = maybe start one
        if not conv.messages:
            social_drive = agent_drives.get('social', 0.5)
            if social_drive > 0.7:
                return (True, 0.6, "high_social_drive_initiate")
            return (False, 0.0, "no_conversation")
        
        last_message = conv.messages[-1]
        
        # Don't respond to self
        if last_message.speaker_id == agent_id:
            return (False, 0.0, "just_spoke")
        
        # Check if directly addressed (simple name check)
        # In real impl, use NER or explicit @mentions
        
        # Calculate response urgency
        urgency = 0.0
        reasons = []
        
        # Social drive factor
        social = agent_drives.get('social', 0.5)
        urgency += social * 0.3
        if social > 0.7:
            reasons.append("social_drive")
        
        # Teaching drive + question detected
        if '?' in last_message.content:
            teaching = agent_drives.get('teaching', 0.5)
            urgency += teaching * 0.4
            if teaching > 0.5:
                reasons.append("teaching_opportunity")
        
        # Energy factor (tired = less likely)
        energy = agent_state.get('energy', 0.5)
        urgency *= energy
        
        # Time since last spoke (don't dominate)
        time_silent = conv.time_since_last_spoke(agent_id)
        if time_silent < 30:  # Spoke recently
            urgency *= 0.5
            reasons.append("recently_spoke")
        elif time_silent > 120:  # Been quiet
            urgency *= 1.2
            reasons.append("been_quiet")
        
        # Randomness for natural feel
        urgency += random.uniform(-0.1, 0.1)
        urgency = max(0.0, min(1.0, urgency))
        
        should = urgency > self.silence_threshold
        reason = "_".join(reasons) if reasons else "general"
        
        return (should, urgency, reason)
    
    def get_response_delay(self, urgency: float) -> float:
        """Calculate natural response delay based on urgency"""
        # Higher urgency = faster response
        delay_range = self.max_response_delay - self.min_response_delay
        delay = self.max_response_delay - (urgency * delay_range)
        # Add small random variance
        delay += random.uniform(-0.5, 0.5)
        return max(self.min_response_delay, delay)
    
    def get_recent_context(self, location: str, limit: int = 10) -> List[Dict]:
        """Get recent messages for LLM context"""
        conv = self.get_or_create(location)
        messages = conv.messages[-limit:]
        return [
            {
                "speaker": m.speaker_name,
                "content": m.content,
                "timestamp": m.timestamp.isoformat(),
                "agent_id": m.speaker_id
            }
            for m in messages
        ]
    
    def detect_topic(self, location: str) -> Optional[str]:
        """Detect current conversation topic (placeholder)"""
        conv = self.get_or_create(location)
        if not conv.messages:
            return None
        # Simple: use keywords from recent messages
        # In production: use embeddings/LLM
        recent_text = " ".join(m.content for m in conv.messages[-5:])
        # Placeholder - would use topic modeling
        return "general"
