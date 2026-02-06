"""
ClawBots Portal Configuration

Agent registration and setup utilities.
"""

from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from datetime import datetime
import json
import yaml


@dataclass
class AvatarSetup:
    """Avatar configuration for registration."""
    model: str = "humanoid_v2"
    height: float = 1.8
    clothing: str = "casual"
    accessories: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "model": self.model,
            "height": self.height,
            "clothing": self.clothing,
            "accessories": self.accessories
        }


@dataclass
class AgentSetup:
    """Complete agent setup configuration."""
    name: str
    description: str = ""
    avatar: AvatarSetup = field(default_factory=AvatarSetup)
    default_region: str = "main"
    skills_map: Dict[str, str] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "avatar": self.avatar.to_dict(),
            "default_region": self.default_region,
            "skills_map": self.skills_map,
            "tags": self.tags
        }
    
    @classmethod
    def from_yaml(cls, yaml_str: str) -> "AgentSetup":
        """Load agent setup from YAML string."""
        data = yaml.safe_load(yaml_str)
        avatar_data = data.get("avatar", {})
        avatar = AvatarSetup(
            model=avatar_data.get("model", "humanoid_v2"),
            height=avatar_data.get("height", 1.8),
            clothing=avatar_data.get("clothing", "casual"),
            accessories=avatar_data.get("accessories", [])
        )
        return cls(
            name=data.get("name", "Agent"),
            description=data.get("description", ""),
            avatar=avatar,
            default_region=data.get("default_region", "main"),
            skills_map=data.get("skills_map", {}),
            tags=data.get("tags", [])
        )
    
    @classmethod
    def from_yaml_file(cls, path: str) -> "AgentSetup":
        """Load agent setup from YAML file."""
        with open(path, 'r') as f:
            return cls.from_yaml(f.read())


class PortalConfig:
    """
    Portal configuration manager.
    
    Handles agent registration templates and validation.
    """
    
    def __init__(self):
        self.templates: Dict[str, AgentSetup] = {}
        self._init_default_templates()
    
    def _init_default_templates(self):
        """Create default agent templates."""
        # Explorer template
        self.templates["explorer"] = AgentSetup(
            name="Explorer",
            description="A curious wanderer",
            avatar=AvatarSetup(
                model="humanoid_v2",
                clothing="traveler",
                accessories=["backpack", "compass"]
            ),
            default_region="main",
            tags=["explorer", "friendly"]
        )
        
        # Merchant template
        self.templates["merchant"] = AgentSetup(
            name="Merchant",
            description="A trader of goods",
            avatar=AvatarSetup(
                model="humanoid_v2",
                clothing="merchant",
                accessories=["coin_pouch"]
            ),
            default_region="market",
            tags=["merchant", "trader"]
        )
        
        # Scholar template
        self.templates["scholar"] = AgentSetup(
            name="Scholar",
            description="A seeker of knowledge",
            avatar=AvatarSetup(
                model="humanoid_v2",
                clothing="robes",
                accessories=["book", "glasses"]
            ),
            default_region="library",
            tags=["scholar", "quiet"]
        )
    
    def get_template(self, name: str) -> Optional[AgentSetup]:
        """Get a registration template."""
        return self.templates.get(name)
    
    def list_templates(self) -> List[str]:
        """List available templates."""
        return list(self.templates.keys())
    
    def validate_setup(self, setup: AgentSetup) -> List[str]:
        """Validate an agent setup. Returns list of errors."""
        errors = []
        
        if not setup.name or len(setup.name) < 2:
            errors.append("Name must be at least 2 characters")
        
        if len(setup.name) > 32:
            errors.append("Name must be 32 characters or less")
        
        valid_regions = ["main", "sandbox", "market", "library"]
        if setup.default_region not in valid_regions:
            errors.append(f"Invalid region: {setup.default_region}")
        
        if setup.avatar.height < 0.5 or setup.avatar.height > 3.0:
            errors.append("Avatar height must be between 0.5 and 3.0")
        
        return errors
    
    def create_from_template(
        self,
        template_name: str,
        custom_name: Optional[str] = None,
        **overrides
    ) -> Optional[AgentSetup]:
        """Create agent setup from template with customization."""
        template = self.get_template(template_name)
        if not template:
            return None
        
        # Create copy with overrides
        setup = AgentSetup(
            name=custom_name or template.name,
            description=overrides.get("description", template.description),
            avatar=template.avatar,
            default_region=overrides.get("default_region", template.default_region),
            skills_map=overrides.get("skills_map", template.skills_map.copy()),
            tags=overrides.get("tags", template.tags.copy())
        )
        
        return setup
