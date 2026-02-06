"""Persona Models"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import yaml

@dataclass
class Archetype:
    role: str  # guide, trickster, observer, etc.
    tone: str  # calm, playful, formal, etc.
    social_position: str = "neutral"  # high, neutral, low

@dataclass
class Expression:
    verbosity: str = "medium"  # very_low, low, medium, high
    humor: str = "low"  # low, medium, high
    formality: str = "medium"
    emotional_range: str = "medium"

@dataclass
class Persona:
    id: str
    display_name: str
    archetype: Archetype
    expression: Expression
    preferred_actions: List[str] = field(default_factory=list)
    avoids: List[str] = field(default_factory=list)
    compatibility: Dict = field(default_factory=dict)
    
    @classmethod
    def from_yaml(cls, path: str) -> "Persona":
        with open(path) as f:
            data = yaml.safe_load(f)
        
        archetype = Archetype(**data.get('archetype', {}))
        expression = Expression(**data.get('expression', {}))
        
        return cls(
            id=data['id'],
            display_name=data['display_name'],
            archetype=archetype,
            expression=expression,
            preferred_actions=data.get('preferred_actions', []),
            avoids=data.get('avoids', []),
            compatibility=data.get('compatibility', {})
        )
    
    def allows_action(self, action: str) -> bool:
        return action not in self.avoids
    
    def prefers_action(self, action: str) -> bool:
        return action in self.preferred_actions
