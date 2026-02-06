"""Soul - Agent's Core Identity (RFC-0001, RFC-0007)

The Soul defines WHO an agent is:
- Identity & name
- Core values (never overridden)
- Allowed personas (masks)
- Relationships
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import yaml

@dataclass
class Soul:
    name: str
    identity: str
    personality: str  # reference to personality template
    drives: str  # reference to drives config
    default_persona: str
    allowed_personas: List[str]
    values: List[str]
    relationships: Dict[str, str] = field(default_factory=dict)
    
    @classmethod
    def from_yaml(cls, path: str) -> "Soul":
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls(**data)
    
    def can_use_persona(self, persona_id: str) -> bool:
        return persona_id in self.allowed_personas
    
    def get_relationship(self, agent_id: str) -> Optional[str]:
        return self.relationships.get(agent_id)
