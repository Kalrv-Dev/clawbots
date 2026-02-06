"""Memory Models"""
from dataclasses import dataclass
from typing import Optional, List, Dict
from enum import Enum
from datetime import datetime

class MemoryType(Enum):
    WORKING = "working"      # Current context
    EPISODIC = "episodic"    # Events/interactions
    SEMANTIC = "semantic"    # Facts/relationships

@dataclass
class Memory:
    id: str
    type: MemoryType
    content: str
    importance: float  # 0-1
    timestamp: datetime
    agent_id: str
    related_agents: List[str] = None
    location: Optional[str] = None
    tags: List[str] = None
    decay_rate: float = 0.01
    
    def should_forget(self, current_time: datetime, threshold: float = 0.1) -> bool:
        """Check if memory should be forgotten (importance decayed below threshold)"""
        elapsed_hours = (current_time - self.timestamp).total_seconds() / 3600
        decayed_importance = self.importance * (1 - self.decay_rate * elapsed_hours)
        return decayed_importance < threshold
