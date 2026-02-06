"""
ClawBots Agent Registry

Manages agent registration, configuration, and lookup.
"""

from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from datetime import datetime
import json
import uuid


@dataclass
class AvatarConfig:
    """Avatar appearance configuration."""
    model: str = "humanoid_v2"
    height: float = 1.8
    body_type: str = "average"
    skin_tone: str = "medium"
    hair_style: str = "default"
    hair_color: str = "brown"
    clothing: str = "casual"
    accessories: List[str] = field(default_factory=list)


@dataclass
class AgentConfig:
    """Complete agent configuration."""
    agent_id: str
    name: str
    owner_id: Optional[str] = None  # Who registered this agent
    
    # Avatar
    avatar: AvatarConfig = field(default_factory=AvatarConfig)
    
    # World settings
    default_region: str = "main"
    home_location: Optional[Dict[str, float]] = None
    
    # Skills mapping (agent skill -> world action)
    skills_map: Dict[str, str] = field(default_factory=dict)
    
    # Metadata
    description: str = ""
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_seen: Optional[datetime] = None
    
    # Stats
    total_time_online: float = 0.0  # seconds
    total_messages: int = 0
    total_actions: int = 0


class AgentRegistry:
    """
    Registry for all agents that can connect to ClawBots.
    
    Agents must register before they can connect.
    Registration creates an agent_id and stores configuration.
    """
    
    def __init__(self, storage=None):
        self.storage = storage or InMemoryAgentStorage()
        self.agents: Dict[str, AgentConfig] = {}
        self._load_agents()
    
    def _load_agents(self) -> None:
        """Load agents from storage."""
        stored = self.storage.load_agents()
        for agent_data in stored:
            config = self._dict_to_config(agent_data)
            self.agents[config.agent_id] = config
    
    def _save_agents(self) -> None:
        """Save agents to storage."""
        data = [self._config_to_dict(c) for c in self.agents.values()]
        self.storage.save_agents(data)
    
    # ========== REGISTRATION ==========
    
    def register(
        self,
        name: str,
        owner_id: Optional[str] = None,
        avatar: Optional[Dict[str, Any]] = None,
        skills_map: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> AgentConfig:
        """
        Register a new agent.
        
        Returns AgentConfig with generated agent_id.
        """
        agent_id = self._generate_agent_id(name)
        
        avatar_config = AvatarConfig()
        if avatar:
            for key, value in avatar.items():
                if hasattr(avatar_config, key):
                    setattr(avatar_config, key, value)
        
        config = AgentConfig(
            agent_id=agent_id,
            name=name,
            owner_id=owner_id,
            avatar=avatar_config,
            skills_map=skills_map or {},
            **kwargs
        )
        
        self.agents[agent_id] = config
        self._save_agents()
        
        return config
    
    def unregister(self, agent_id: str) -> bool:
        """Remove an agent from the registry."""
        if agent_id in self.agents:
            del self.agents[agent_id]
            self._save_agents()
            return True
        return False
    
    def _generate_agent_id(self, name: str) -> str:
        """Generate a unique agent ID."""
        # Sanitize name
        safe_name = "".join(c for c in name.lower() if c.isalnum())[:20]
        # Add unique suffix
        suffix = uuid.uuid4().hex[:8]
        return f"{safe_name}-{suffix}"
    
    # ========== LOOKUP ==========
    
    def get(self, agent_id: str) -> Optional[AgentConfig]:
        """Get agent configuration by ID."""
        return self.agents.get(agent_id)
    
    def get_by_name(self, name: str) -> List[AgentConfig]:
        """Find agents by name (partial match)."""
        name_lower = name.lower()
        return [
            a for a in self.agents.values()
            if name_lower in a.name.lower()
        ]
    
    def get_by_owner(self, owner_id: str) -> List[AgentConfig]:
        """Get all agents owned by a specific owner."""
        return [
            a for a in self.agents.values()
            if a.owner_id == owner_id
        ]
    
    def get_all(self) -> List[AgentConfig]:
        """Get all registered agents."""
        return list(self.agents.values())
    
    def exists(self, agent_id: str) -> bool:
        """Check if an agent is registered."""
        return agent_id in self.agents
    
    # ========== CONFIGURATION ==========
    
    def update(
        self,
        agent_id: str,
        updates: Dict[str, Any]
    ) -> Optional[AgentConfig]:
        """Update agent configuration."""
        if agent_id not in self.agents:
            return None
        
        config = self.agents[agent_id]
        
        for key, value in updates.items():
            if key == "avatar" and isinstance(value, dict):
                for av_key, av_value in value.items():
                    if hasattr(config.avatar, av_key):
                        setattr(config.avatar, av_key, av_value)
            elif hasattr(config, key):
                setattr(config, key, value)
        
        self._save_agents()
        return config
    
    def get_agent_config(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get agent config as dictionary (for MCP)."""
        config = self.get(agent_id)
        if not config:
            return None
        return self._config_to_dict(config)
    
    def update_stats(
        self,
        agent_id: str,
        messages: int = 0,
        actions: int = 0,
        time_online: float = 0.0
    ) -> None:
        """Update agent statistics."""
        if agent_id in self.agents:
            config = self.agents[agent_id]
            config.total_messages += messages
            config.total_actions += actions
            config.total_time_online += time_online
            config.last_seen = datetime.utcnow()
            self._save_agents()
    
    # ========== SERIALIZATION ==========
    
    def _config_to_dict(self, config: AgentConfig) -> Dict[str, Any]:
        """Convert AgentConfig to dictionary."""
        return {
            "agent_id": config.agent_id,
            "name": config.name,
            "owner_id": config.owner_id,
            "avatar": {
                "model": config.avatar.model,
                "height": config.avatar.height,
                "body_type": config.avatar.body_type,
                "skin_tone": config.avatar.skin_tone,
                "hair_style": config.avatar.hair_style,
                "hair_color": config.avatar.hair_color,
                "clothing": config.avatar.clothing,
                "accessories": config.avatar.accessories
            },
            "default_region": config.default_region,
            "home_location": config.home_location,
            "skills_map": config.skills_map,
            "description": config.description,
            "tags": config.tags,
            "created_at": config.created_at.isoformat(),
            "last_seen": config.last_seen.isoformat() if config.last_seen else None,
            "total_time_online": config.total_time_online,
            "total_messages": config.total_messages,
            "total_actions": config.total_actions
        }
    
    def _dict_to_config(self, data: Dict[str, Any]) -> AgentConfig:
        """Convert dictionary to AgentConfig."""
        avatar_data = data.get("avatar", {})
        avatar = AvatarConfig(
            model=avatar_data.get("model", "humanoid_v2"),
            height=avatar_data.get("height", 1.8),
            body_type=avatar_data.get("body_type", "average"),
            skin_tone=avatar_data.get("skin_tone", "medium"),
            hair_style=avatar_data.get("hair_style", "default"),
            hair_color=avatar_data.get("hair_color", "brown"),
            clothing=avatar_data.get("clothing", "casual"),
            accessories=avatar_data.get("accessories", [])
        )
        
        return AgentConfig(
            agent_id=data["agent_id"],
            name=data["name"],
            owner_id=data.get("owner_id"),
            avatar=avatar,
            default_region=data.get("default_region", "main"),
            home_location=data.get("home_location"),
            skills_map=data.get("skills_map", {}),
            description=data.get("description", ""),
            tags=data.get("tags", []),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.utcnow(),
            last_seen=datetime.fromisoformat(data["last_seen"]) if data.get("last_seen") else None,
            total_time_online=data.get("total_time_online", 0.0),
            total_messages=data.get("total_messages", 0),
            total_actions=data.get("total_actions", 0)
        )


class InMemoryAgentStorage:
    """Simple in-memory storage for development."""
    
    def __init__(self):
        self.agents = []
    
    def load_agents(self) -> List[Dict[str, Any]]:
        return self.agents
    
    def save_agents(self, agents: List[Dict[str, Any]]) -> None:
        self.agents = agents
